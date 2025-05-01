from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

# Setup Flask
app = Flask(__name__)
CORS(app, resources={r"/summarize": {"origins": "https://solusiai.free.nf"}})

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

@app.route("/", methods=["GET"])
def home():
    return "YouTube Summarizer API is running 🚀", 200

@app.route("/summarize", methods=["POST", "OPTIONS"])
def summarize():
    if request.method == "OPTIONS":
        return '', 200

    try:
        data = request.get_json(force=True)
        video_url = data.get("video_url", "").strip()
        print(f"[INFO] URL diterima: {video_url}")

        # Validasi input
        if not video_url:
            return jsonify({"error": "Parameter 'video_url' tidak ditemukan"}), 400

        # Ekstraksi video ID
        video_id = ""
        parsed_url = urlparse(video_url)

        if "youtube.com" in parsed_url.netloc:
            video_id = parse_qs(parsed_url.query).get("v", [""])[0]
        elif "youtu.be" in parsed_url.netloc:
            video_id = parsed_url.path.lstrip("/")

        if not video_id:
            return jsonify({"error": "URL video tidak valid"}), 400

        print(f"[DEBUG] video_id: {video_id}")

        # Ambil transkrip
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["id"])
        except Exception as e_id:
            print(f"[WARNING] Transkrip Bahasa Indonesia tidak tersedia, mencoba Bahasa Inggris: {str(e_id)}")
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
            except Exception as e_en:
                print(f"[ERROR] Tidak ada transkrip tersedia: {str(e_en)}")
                return jsonify({"error": "Transkrip tidak tersedia dalam Bahasa Indonesia atau Inggris."}), 404

        content = " ".join([t["text"] for t in transcript])
        print(f"[INFO] Panjang transkrip: {len(content.split())} kata")

        prompt = f"Tolong buatkan ringkasan dalam bentuk poin-poin dari isi video berikut dalam bahasa Indonesia:\n\n{content}"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": "YouTube Summarizer"
        }

        payload = {
            "model": "deepseek/deepseek-r1:free",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that summarizes YouTube videos."},
                {"role": "user", "content": prompt}
            ]
        }

        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)

        print(f"[INFO] Status response OpenRouter: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            summary = result["choices"][0]["message"]["content"]
            return jsonify({"summary": summary})
        else:
            print(f"[ERROR] OpenRouter gagal: {response.text}")
            return jsonify({"error": "Gagal meringkas video", "details": response.text}), 500

    except Exception as e:
        print(f"[FATAL] Exception tidak terduga: {str(e)}")
        return jsonify({"error": "Terjadi kesalahan internal", "details": str(e)}), 500

# Run on Railway
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[DEBUG] Running on port: {port}")
    app.run(host="0.0.0.0", port=port)
