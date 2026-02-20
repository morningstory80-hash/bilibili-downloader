from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "Server is running perfectly!"

@app.route('/get-video', methods=['GET', 'POST'])
def get_video():
    if request.method == 'POST':
        url = request.json.get('url')
    else:
        url = request.args.get('url')
        
    if not url:
        return jsonify({"error": "দয়া করে একটি Bilibili লিংক দিন"}), 400
    
    # Bilibili এর জন্য আপডেট করা সেটিং
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # স্মার্ট লিংক এক্সট্রাকশন
            video_url = info.get('url')
            if not video_url and 'requested_formats' in info:
                # ভিডিও এবং অডিও আলাদা থাকলে প্রথম লিংকটা নেবে
                video_url = info['requested_formats'][0].get('url')
                
            title = info.get('title', 'No Title Found')
            description = info.get('description', '')
            
            return jsonify({
                "success": True,
                "title": title,
                "description": description,
                "video_url": video_url
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
    
