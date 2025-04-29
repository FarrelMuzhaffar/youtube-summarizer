
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
if not api_key:
    raise Exception("API Key OpenRouter tidak ditemukan di environment variable.")



# Fungsi ambil transkrip YouTube
def get_transcript(video_url):
    try:
        video_id = video_url.split("v=")[-1].split("&")[0]
        try:
            # Prioritaskan transkrip bahasa Indonesia
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['id'])
        except:
            # Fallback ke bahasa Inggris jika tidak ada transkrip Indonesia
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        text = " ".join([t['text'] for t in transcript])
        return text
    except Exception as e:
        return None

# Endpoint API
@app.route("/summarize", methods=["POST"])
def summarize():
    data = request.get_json()
    video_url = data.get("video_url")



@app.route("/", methods=["GET"])
def home():
    return "YouTube Summarizer API is running 🚀", 200




    if not video_url:
        return jsonify({"error": "URL video tidak ditemukan"}), 400

    content = get_transcript(video_url)
    if not content:
        return jsonify({"error": "Gagal mengambil transkrip"}), 400

    # Prompt selalu dalam bahasa Indonesia
    prompt = f"Tolong buatkan ringkasan dalam bentuk poin-poin dari isi video berikut dalam bahasa Indonesia:\n\n{content}"

    # Request ke OpenRouter
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost/solusiai/youtube-summarizer",
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
        return jsonify({"error": "Gagal meringkas video", "details": response.text}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # ambil PORT dari environment variable
    app.run(host="0.0.0.0", port=port)
