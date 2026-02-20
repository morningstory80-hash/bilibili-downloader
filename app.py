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
    
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            video_url = info.get('url')
            title = info.get('title')
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
    
