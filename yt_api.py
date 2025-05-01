from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi

# Setup Flask
app = Flask(__name__)

# FIX CORS untuk domain WordPress
CORS(app, resources={r"/summarize": {"origins": "https://solusiai.free.nf"}})

# Load API Key dari .env
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
        print(f"[DEBUG] Data diterima: {data}")

        if not data or "video_url" not in data:
            print("[ERROR] video_url tidak ditemukan dalam request")
            return jsonify({"error": "Parameter 'video_url' tidak ditemukan"}), 400

        video_url = data["video_url"]
        print(f"[DEBUG] video_url: {video_url}")

        try:
            transcript = YouTubeTranscriptApi.get_transcript(
                video_url.split("v=")[-1].split("&")[0], languages=["id"]
            )
        except Exception as e:
            print(f"[WARNING] Transkrip bahasa Indonesia tidak tersedia, mencoba bahasa Inggris. Detail: {e}")
            transcript = YouTubeTranscriptApi.get_transcript(
                video_url.split("v=")[-1].split("&")[0], languages=["en"]
            )

        content = " ".join([t["text"] for t in transcript])
        print(f"[DEBUG] Jumlah kata transkrip: {len(content.split())}")

        prompt = f"Tolong buatkan ringkasan dalam bentuk poin-poin dari isi video berikut dalam bahasa Indonesia:\n\n{content}"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://solusiai.free.nf/summarize-ai",
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
        print(f"[DEBUG] Response status dari OpenRouter: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            return jsonify({"summary": result["choices"][0]["message"]["content"]})
        else:
            print(f"[ERROR] Gagal meringkas: {response.status_code} - {response.text}")
            return jsonify({"error": "Gagal meringkas video", "details": response.text}), 500

    except Exception as e:
        print(f"[ERROR] Terjadi exception fatal: {str(e)}")
        return jsonify({"error": "Terjadi error internal", "details": str(e)}), 500


# Jalankan aplikasi Flask di Railway
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[DEBUG] Running on port: {port}")
    app.run(host="0.0.0.0", port=port)
