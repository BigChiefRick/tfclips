from flask import Flask
import os
import requests
from datetime import datetime, timedelta
import json
import re

app = Flask(__name__)

CLIENT_ID = os.environ.get('TWITCH_CLIENT_ID')
CLIENT_SECRET = os.environ.get('TWITCH_CLIENT_SECRET')

def get_ticklefitz_clips_with_mp4():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise Exception("Twitch API credentials not configured")
    
    token_response = requests.post('https://id.twitch.tv/oauth2/token', {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }, timeout=10)
    
    if token_response.status_code != 200:
        raise Exception("Failed to get Twitch access token")
    
    token = token_response.json()['access_token']
    
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {token}'
    }
    
    user_response = requests.get('https://api.twitch.tv/helix/users?login=ticklefitz', 
                               headers=headers, timeout=10)
    
    if user_response.status_code != 200:
        raise Exception("Failed to find TickleFitz on Twitch")
    
    user_data = user_response.json()
    if not user_data['data']:
        raise Exception("TickleFitz user not found")
    
    user_id = user_data['data'][0]['id']
    
    start_time = (datetime.now() - timedelta(days=30)).isoformat() + 'Z'
    
    clips_response = requests.get('https://api.twitch.tv/helix/clips', {
        'broadcaster_id': user_id,
        'first': 20,
        'started_at': start_time
    }, headers=headers, timeout=10)
    
    if clips_response.status_code != 200:
        raise Exception("Failed to fetch TickleFitz clips")
    
    clips_data = clips_response.json()['data']
    
    if not clips_data:
        raise Exception("No TickleFitz clips found in the last 30 days")
    
    # Sort by view count and extract MP4 URLs
    clips_data.sort(key=lambda x: x['view_count'], reverse=True)
    
    clips_with_mp4 = []
    for clip in clips_data:
        # Extract MP4 URL from thumbnail URL
        thumbnail_url = clip['thumbnail_url']
        print(f"DEBUG: Processing clip '{clip['title']}'")
        print(f"DEBUG: Thumbnail URL: {thumbnail_url}")
        
        # Try multiple regex patterns for different Twitch CDN formats
        patterns = [
            r'(https://clips-media-assets2\.twitch\.tv/.*)-preview',
            r'(https://clips-media-assets\.twitch\.tv/.*)-preview', 
            r'(https://production\.assets\.clips\.twitchcdn\.net/.*)-preview'
        ]
        
        mp4_url = None
        for pattern in patterns:
            mp4_match = re.search(pattern, thumbnail_url)
            if mp4_match:
                mp4_url = mp4_match.group(1) + '.mp4'
                print(f"DEBUG: Found MP4 URL: {mp4_url}")
                break
        
        if mp4_url:
            clips_with_mp4.append({
                'title': clip['title'],
                'mp4_url': mp4_url,
                'view_count': clip['view_count'],
                'creator_name': clip['creator_name'],
                'duration': clip['duration']
            })
        else:
            print(f"DEBUG: Could not extract MP4 URL from thumbnail")
    
    print(f"DEBUG: Found {len(clips_with_mp4)} clips with MP4 URLs out of {len(clips_data)} total clips")
    return clips_with_mp4

@app.route('/')
def clips():
    try:
        clips_data = get_ticklefitz_clips_with_mp4()
        if not clips_data:
            # If no MP4 URLs found, show debug info
            return '''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>body{margin:0;background:#000;color:#fff;font-family:Arial;padding:20px;}
pre{background:#333;padding:15px;border-radius:5px;overflow:auto;}
</style></head>
<body>
<h1>Debug: No MP4 URLs Found</h1>
<p>Check Heroku logs for thumbnail URL patterns.</p>
<p>The regex might need updating for current Twitch CDN format.</p>
</body></html>'''
    except Exception as e:
        return f'''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>body{{margin:0;background:#000;color:#fff;font-family:Arial;text-align:center;padding:50px;}}
.error{{background:#e74c3c;padding:30px;border-radius:10px;max-width:600px;margin:0 auto;}}
</style></head>
<body><div class="error"><h1>Error Loading TickleFitz Clips</h1><p>{str(e)}</p>
<p>Check Twitch API credentials in Heroku config vars.</p></div></body></html>'''
    
    clips_json = json.dumps(clips_data)
    
    html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { margin: 0; background: #000; color: #fff; font-family: Arial; overflow: hidden; }
        .container { width: 100vw; height: 100vh; position: relative; }
        video { width: 100%; height: 100%; object-fit: cover; }
        .info { position: absolute; bottom: 20px; left: 20px; background: rgba(0,0,0,0.8); padding: 15px; border-radius: 10px; border-left: 4px solid #9146ff; }
        .progress { position: absolute; bottom: 0; left: 0; height: 4px; background: #9146ff; transition: width 0.1s; }
    </style>
</head>
<body>
    <div class="container">
        <video id="player" autoplay muted></video>
        <div class="info">
            <div id="title">TickleFitz Clips</div>
            <div>Clip <span id="num">1</span> of ''' + str(len(clips_data)) + '''</div>
            <div id="details" style="font-size: 12px; color: #ccc; margin-top: 5px;"></div>
        </div>
        <div id="progress" class="progress" style="width: 0%;"></div>
    </div>
    <script>
        const clips = ''' + clips_json + ''';
        let currentIndex = 0;
        let progressTimer;
        
        const player = document.getElementById('player');
        
        // Unmute after user interaction (required for autoplay)
        document.addEventListener('click', () => {
            player.muted = false;
            console.log('Audio enabled');
        });
        
        // Auto-unmute attempt
        setTimeout(() => {
            player.muted = false;
        }, 2000);
        
        function playClip() {
            if (clips.length === 0) return;
            
            const clip = clips[currentIndex];
            player.src = clip.mp4_url;
            
            document.getElementById('title').textContent = clip.title;
            document.getElementById('num').textContent = currentIndex + 1;
            document.getElementById('details').textContent = `👁️ ${clip.view_count.toLocaleString()} views • 👤 ${clip.creator_name}`;
            
            // Reset progress
            document.getElementById('progress').style.width = '0%';
            
            console.log(`Playing: ${clip.title} (${clip.view_count} views)`);
        }
        
        // Handle video end - move to next clip
        player.addEventListener('ended', () => {
            currentIndex = (currentIndex + 1) % clips.length;
            setTimeout(playClip, 500); // Small delay between clips
        });
        
        // Progress bar based on video duration
        player.addEventListener('timeupdate', () => {
            if (player.duration > 0) {
                const progress = (player.currentTime / player.duration) * 100;
                document.getElementById('progress').style.width = progress + '%';
            }
        });
        
        // Start playing
        setTimeout(playClip, 1000);
        
        console.log(`Loaded ${clips.length} TickleFitz clips with direct MP4 URLs`);
    </script>
</body>
</html>'''
    
    return html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
