from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app) # যাতে আপনার ওয়েবসাইট থেকে রিকোয়েস্ট পাঠালে ব্লক না হয়

@app.route('/get-video', methods=['GET', 'POST'])
def get_video():
    # রিকোয়েস্ট থেকে লিংক নেওয়া
    if request.method == 'POST':
        url = request.json.get('url')
    else:
        url = request.args.get('url')
        
    if not url:
        return jsonify({"error": "দয়া করে একটি Bilibili লিংক দিন"}), 400
    
    # yt-dlp এর সেটিং (শুধুমাত্র লিংক বের করবে, ডাউনলোড করবে না)
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # ভিডিওর আসল লিংক এবং টাইটেল বের করা
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
  
