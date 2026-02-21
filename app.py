import os
import threading
import subprocess
import imageio_ffmpeg
import google.generativeai as genai
from flask import Flask, request, jsonify, redirect, url_for, session
import yt_dlp
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

app = Flask(__name__)
app.secret_key = 'morningstory_super_secret'

# --- এআই (Gemini) সেটআপ ---
GEMINI_API_KEY = "AIzaSyBe95g0PChKprH7V66EMttuUIOXo5tX4n0"
genai.configure(api_key=GEMINI_API_KEY)

# --- ইউটিউব সেটআপ ---
CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# ==========================================
# ১. পারমানেন্ট লগইন সিস্টেম (আজীবন চাবি তৈরি)
# ==========================================
@app.route('/login')
def login():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    # prompt='consent' দিলে আজীবনের জন্য রিফ্রেশ টোকেন পাওয়া যায়
    authorization_url, state = flow.authorization_url(access_type='offline', prompt='consent')
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    flow.fetch_token(authorization_response=request.url)
    
    credentials = flow.credentials
    with open('token.json', 'w') as f:
        f.write(credentials.to_json())
    return "ইউটিউব সাকসেসফুলি কানেক্ট হয়েছে! এবার পারমানেন্ট চাবি পেতে আপনার লিংকের শেষে /show_token লিখে সার্চ করুন।"

@app.route('/show_token')
def show_token():
    try:
        with open('token.json', 'r') as f:
            return f.read()
    except:
        return "টোকেন পাওয়া যায়নি! আগে /login করে কানেক্ট করুন।"

# ==========================================
# ২. সুপার ভিডিও প্রসেসর (FFmpeg + Make.com)
# ==========================================
def process_video_background(video_url):
    try:
        print(f"কাজ শুরু হচ্ছে: {video_url}")
        
        # ১. ভিডিও এবং থাম্বনেইল ডাউনলোড
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
            'outtmpl': 'raw_video.%(ext)s',
            'writethumbnail': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            chinese_title = info.get('title', 'Unknown Title')
            
        # ২. এআই (Gemini) দিয়ে মেটাডেটা তৈরি
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"Translate this Chinese video title '{chinese_title}' to Bengali. Write a very attractive YouTube video title, a short description, and 10 viral tags separated by commas. Format exactly like this:\nTITLE: [your title]\nDESC: [your desc]\nTAGS: [tag1, tag2]"
        ai_response = model.generate_content(prompt).text
        
        title = ai_response.split('TITLE:')[1].split('DESC:')[0].strip() if 'TITLE:' in ai_response else "New Viral Video"
        desc = ai_response.split('DESC:')[1].split('TAGS:')[0].strip() if 'DESC:' in ai_response else "Watch this amazing video!"
        tags_str = ai_response.split('TAGS:')[1].strip() if 'TAGS:' in ai_response else "viral, trending"
        tags = [tag.strip() for tag in tags_str.split(',')]

        # ৩. FFmpeg দিয়ে ইনভিজিবল এডিট (র‍্যাম খাবে না, অডিও অরিজিনাল থাকবে)
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg_exe,
            '-i', 'raw_video.mp4',
            '-i', 'logo.png',
            '-filter_complex', '[0:v]eq=saturation=1.05[bg];[bg][1:v]overlay=W-w-20:20', # কালার ৫% বৃদ্ধি এবং ডানদিকের কোণায় লোগো
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-c:a', 'copy', # অডিও ১০০% অরিজিনাল
            '-map_metadata', '-1', # চাইনিজ লুকানো মেটাডেটা রিমুভ
            '-y', 'edited_video.mp4'
        ]
        subprocess.run(cmd, check=True)

        # ৪. ইউটিউবে আপলোড
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        youtube = build('youtube', 'v3', credentials=creds)
        
        thumb_file = [f for f in os.listdir('.') if f.startswith('raw_video') and not f.endswith('.mp4')]
        thumb_path = thumb_file[0] if thumb_file else None

        request_body = {
            'snippet': {
                'title': title,
                'description': desc,
                'tags': tags,
                'categoryId': '24'
            },
            'status': {
                'privacyStatus': 'public'
            }
        }

        media = MediaFileUpload("edited_video.mp4", chunksize=-1, resumable=True)
        upload_req = youtube.videos().insert(part=','.join(request_body.keys()), body=request_body, media_body=media)
        response = upload_req.execute()
        video_id = response.get('id')
        
        if thumb_path:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumb_path)).execute()

        # ৫. জায়গা বাঁচাতে সার্ভার থেকে ফাইল ডিলিট
        os.remove("raw_video.mp4")
        os.remove("edited_video.mp4")
        if thumb_path:
            os.remove(thumb_path)

    except Exception as e:
        print(f"Error: {e}")

@app.route('/process', methods=['POST'])
def process():
    data = request.json
    video_url = data.get('url')
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400
    
    thread = threading.Thread(target=process_video_background, args=(video_url,))
    thread.start()
    return jsonify({"message": "প্রসেসিং এবং আপলোড শুরু হয়েছে!"}), 200

@app.route('/')
def home():
    return "Morning Story Super FFmpeg Robot is Running!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
