from flask import Flask
import os
import requests
from datetime import datetime, timedelta
import json

app = Flask(__name__)

CLIENT_ID = os.environ.get('TWITCH_CLIENT_ID')
CLIENT_SECRET = os.environ.get('TWITCH_CLIENT_SECRET')

def get_ticklefitz_clips():
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
    
    clips_data.sort(key=lambda x: x['view_count'], reverse=True)
    
    return [clip['id'] for clip in clips_data]

@app.route('/')
def clips():
    try:
        clip_ids = get_ticklefitz_clips()
    except Exception as e:
        return f'''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>body{{margin:0;background:#000;color:#fff;font-family:Arial;text-align:center;padding:50px;}}
.error{{background:#e74c3c;padding:30px;border-radius:10px;max-width:600px;margin:0 auto;}}
</style></head>
<body><div class="error"><h1>Error Loading TickleFitz Clips</h1><p>{str(e)}</p>
<p>Check Twitch API credentials in Heroku config vars.</p></div></body></html>'''
    
    clips_json = json.dumps(clip_ids)
    
    html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { margin: 0; background: #000; color: #fff; font-family: Arial; overflow: hidden; }
        .container { width: 100vw; height: 100vh; position: relative; }
        iframe { width: 100%; height: 100%; border: none; }
        .info { position: absolute; bottom: 20px; left: 20px; background: rgba(0,0,0,0.8); padding: 15px; border-radius: 10px; border-left: 4px solid #9146ff; }
        .progress { position: absolute; bottom: 0; left: 0; height: 4px; background: #9146ff; transition: width 0.1s; }
    </style>
</head>
<body>
    <div class="container">
        <iframe id="player" 
                allow="autoplay; fullscreen" 
                allowfullscreen>
        </iframe>
        <div class="info">
            <div id="title">TickleFitz Clips</div>
            <div>Clip <span id="num">1</span> of ''' + str(len(clip_ids)) + '''</div>
        </div>
        <div id="progress" class="progress" style="width: 0%;"></div>
    </div>
    <script>
        const clips = ''' + clips_json + ''';
        let i = 0;
        
        function play() {
            const player = document.getElementById('player');
            
            // Use the exact Heroku app domain as parent
            const parentDomain = window.location.hostname;
            
            // Try different Twitch player URL formats
            const playerUrl = `https://clips.twitch.tv/embed?clip=${clips[i]}&parent=${parentDomain}&autoplay=true&muted=false`;
            
            player.src = playerUrl;
            
            console.log(`Playing clip: ${clips[i]} with parent: ${parentDomain}`);
            console.log(`URL: ${playerUrl}`);
            
            document.getElementById('num').textContent = i + 1;
            document.getElementById('title').textContent = `TickleFitz Clip ${i + 1}`;
            document.getElementById('progress').style.width = '0%';
            
            let progress = 0;
            const timer = setInterval(() => {
                progress += 100 / 300;
                document.getElementById('progress').style.width = Math.min(progress, 100) + '%';
                if (progress >= 100) clearInterval(timer);
            }, 100);
            
            i = (i + 1) % clips.length;
            
            setTimeout(() => {
                document.getElementById('progress').style.width = '0%';
                setTimeout(play, 100);
            }, 30000);
        }
        
        setTimeout(play, 1000);
        
        console.log('Loaded ' + clips.length + ' TickleFitz clips - trying player.twitch.tv');
    </script>
</body>
</html>'''
    
    return html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
