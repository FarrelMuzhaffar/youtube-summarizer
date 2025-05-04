from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import re
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup Flask
app = Flask(__name__)
CORS(app, resources={r"/summarize": {"origins": ["https://lintasai.com"]}})

# Load API Key dari .env
load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")
logger.info(f"API Key loaded: {'[REDACTED]' if api_key else 'None'}")  # Log tanpa menampilkan API Key

# Fungsi ekstrak video ID
def extract_video_id(url):
    patterns = [
        r'(?:v=|youtu\.be/)([0-9A-Za-z_-]{11})',
        r'youtube\.com/watch\?v=([0-9A-Za-z_-]{11})',
        r'youtube\.com/embed/([0-9A-Za-z_-]{11})',
        r'youtube\.com/v/([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

@app.route("/", methods=["GET"])
def home():
    return "YouTube Summarizer API is running 🚀", 200

@app.route("/summarize", methods=["POST", "OPTIONS"])
def summarize():
    if request.method == "OPTIONS":
        return '', 200

    try:
        data = request.get_json(force=True)
        logger.info(f"Data diterima: {data}")

        if not data or "video_url" not in data:
            logger.error("video_url tidak ditemukan dalam request")
            return jsonify({"error": "Parameter 'video_url' diperlukan"}), 400

        video_url = data["video_url"]
        logger.info(f"video_url: {video_url}")

        video_id = extract_video_id(video_url)
        if not video_id:
            logger.error("URL YouTube tidak valid")
            return jsonify({"error": "URL YouTube tidak valid"}), 400

        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["id"])
        except (TranscriptsDisabled, NoTranscriptFound):
            logger.warning("Transkrip bahasa Indonesia tidak tersedia, mencoba bahasa Inggris")
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
            except (TranscriptsDisabled, NoTranscriptFound):
                logger.error("Tidak ada transkrip tersedia untuk video ini")
                return jsonify({"error": "Tidak ada transkrip tersedia untuk video ini"}), 400

        content = " ".join([t["text"] for t in transcript])
        logger.info(f"Jumlah kata transkrip: {len(content.split())}")

        if len(content.split()) > 10000:
            content = " ".join(content.split()[:10000])
            logger.warning("Transkrip dipotong menjadi 10.000 kata")

        if not api_key:
            logger.error("API Key OpenRouter tidak ditemukan di environment!")
            return jsonify({"error": "API Key tidak tersedia"}), 500

        prompt = f"Tolong buatkan ringkasan dalam bentuk poin-poin dari isi video berikut dalam bahasa Indonesia:\n\n{content}"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://lintasai.com/youtube-summarizer-ai/",
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
        logger.info(f"Status code dari OpenRouter: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"Error dari OpenRouter: {response.status_code} - {response.text}")
            return jsonify({
                "error": "Gagal meringkas video",
                "details": response.text,
                "status_code": response.status_code
            }), 500

        try:
            result = response.json()
            summary = result["choices"][0]["message"]["content"]
            return jsonify({"summary": summary})
        except Exception as e:
            logger.error(f"Gagal parsing JSON dari OpenRouter: {str(e)}")
            return jsonify({"error": "Gagal membaca respons dari OpenRouter", "details": str(e)}), 500

    except Exception as e:
        logger.error(f"Terjadi exception fatal: {str(e)}")
        return jsonify({"error": "Terjadi error internal", "details": str(e)}), 500

# Jalankan aplikasi Flask di Railway
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Running on port: {port}")
    app.run(host="0.0.0.0", port=port)