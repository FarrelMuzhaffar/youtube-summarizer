from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi

# Setup Flask
app = Flask(__name__)
CORS(app)

# Load API Key dari .env
load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

# Fungsi ambil transkrip YouTube
def get_transcript(video_url):
    try:
        video_id = video_url.split("v=")[-1].split("&")[0]
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['id'])
        except:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        text = " ".join([t['text'] for t in transcript])
        return text
    except Exception as e:
        print(f"[ERROR] Gagal mengambil transkrip: {e}")
        return None

# Route root (untuk test)
@app.route("/", methods=["GET"])
def home():
    return "YouTube Summarizer API is running 🚀", 200

# Route untuk merangkum
@app.route("/summarize", methods=["POST", "OPTIONS"])
def summarize():
    if request.method == "OPTIONS":
        return '', 200  # Handle preflight CORS

    try:
        data = request.get_json(force=True)
        print(f"[DEBUG] Data diterima: {data}")

        if not data or "video_url" not in data:
            return jsonify({"error": "Parameter 'video_url' tidak ditemukan"}), 400

        video_url = data["video_url"]
        content = get_transcript(video_url)

        if not content:
            return jsonify({"error": "Gagal mengambil transkrip"}), 400

        prompt = f"Tolong buatkan ringkasan dalam bentuk poin-poin dari isi video berikut dalam bahasa Indonesia:\n\n{content}"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://solusiai.free.nf",
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

        if response.status_code == 200:
            result = response.json()
            return jsonify({"summary": result["choices"][0]["message"]["content"]})
        else:
            print(f"[ERROR] OpenRouter error: {response.status_code} - {response.text}")
            return jsonify({"error": "Gagal meringkas video", "details": response.text}), 500

    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        return jsonify({"error": "Terjadi error internal", "details": str(e)}), 500

# Jalankan di Railway
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
