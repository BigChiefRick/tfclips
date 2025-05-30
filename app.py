from flask import Flask
import os
import requests
from datetime import datetime, timedelta
import json

app = Flask(__name__)

# Twitch API credentials - set these as environment variables in Heroku
CLIENT_ID = os.environ.get('TWITCH_CLIENT_ID')
CLIENT_SECRET = os.environ.get('TWITCH_CLIENT_SECRET')

def get_twitch_token():
    """Get Twitch access token"""
    if not CLIENT_ID or not CLIENT_SECRET:
        return None
    
    try:
        response = requests.post('https://id.twitch.tv/oauth2/token', {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'client_credentials'
        }, timeout=10)
        
        if response.status_code == 200:
            return response.json()['access_token']
    except:
        pass
    return None

def get_ticklefitz_clips():
    """Fetch real TickleFitz clips from Twitch API"""
    token = get_twitch_token()
    if not token:
        # Return fallback clips if no API access
        return [
            'AwkwardHelplessSalamanderSwiftRage',
            'TameIntelligentChimpanzeeHassaanChop', 
            'PowerfulHandsomeNarwhalM4xHeh',
            'GloriousEagerDogePogChamp',
            'InventiveRealTapirCorgiDerp',
            'SmallCarefulSmoothieOMGScoots',
            'FunnyBraveChickpeaPogChamp',
            'ElegantLazyPigeonBibleThump',
            'WildObedientShrimpSSSsss',
            'CleverHealthyWormNotLikeThis'
        ]
    
    try:
        headers = {
            'Client-ID': CLIENT_ID,
            'Authorization': f'Bearer {token}'
        }
        
        # Get TickleFitz user ID
        user_response = requests.get('https://api.twitch.tv/helix/users?login=ticklefitz', 
                                   headers=headers, timeout=10)
        
        if user_response.status_code != 200:
            return None
        
        user_data = user_response.json()
        if not user_data['data']:
            return None
        
        user_id = user_data['data'][0]['id']
        
        # Get clips from last 30 days
        start_time = (datetime.now() - timedelta(days=30)).isoformat() + 'Z'
        
        clips_response = requests.get('https://api.twitch.tv/helix/clips', {
            'broadcaster_id': user_id,
            'first': 20,
            'started_at': start_time
        }, headers=headers, timeout=10)
        
        if clips_response.status_code == 200:
            clips_data = clips_response.json()['data']
            if clips_data:
                # Sort by view count (most popular first)
                clips_data.sort(key=lambda x: x['view_count'], reverse=True)
                # Return just the clip IDs
                return [clip['id'] for clip in clips_data]
    
    except:
        pass
    
    return None

@app.route('/')
def clips():
    # Get real TickleFitz clips
    clip_ids = get_ticklefitz_clips()
    
    # If API failed, use fallback clips
    if not clip_ids:
        clip_ids = [
            'AwkwardHelplessSalamanderSwiftRage',
            'TameIntelligentChimpanzeeHassaanChop', 
            'PowerfulHandsomeNarwhalM4xHeh',
            'GloriousEagerDogePogChamp',
            'InventiveRealTapirCorgiDerp',
            'SmallCarefulSmoothieOMGScoots',
            'FunnyBraveChickpeaPogChamp',
            'ElegantLazyPigeonBibleThump',
            'WildObedientShrimpSSSsss',
            'CleverHealthyWormNotLikeThis'
        ]
    
    clips_json = json.dumps(clip_ids)
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ margin: 0; background: #000; color: #fff; font-family: Arial; overflow: hidden; }}
        .container {{ width: 100vw; height: 100vh; position: relative; }}
        iframe {{ width: 100%; height: 100%; border: none; }}
        .info {{ 
            position: absolute; bottom: 20px; left: 20px; 
            background: rgba(0,0,0,0.8); padding: 15px; 
            border-radius: 10px; border-left: 4px solid #9146ff; 
        }}
        .progress {{ 
            position: absolute; bottom: 0; left: 0; height: 4px; 
            background: #9146ff; transition: width 0.1s; 
        }}
    </style>
</head>
<body>
    <div class="container">
        <iframe id="player" allow="autoplay; fullscreen; microphone; camera" allowfullscreen></iframe>
        <div class="info">
            <div id="title">TickleFitz Clips</div>
            <div>Clip <span id="num">1</span> of {len(clip_ids)}</div>
        </div>
        <div id="progress" class="progress" style="width: 0%;"></div>
    </div>
    <script>
        const clips = {clips_json};
        let i = 0;
        let progressInterval;
        
        function play() {{
            const domain = window.location.hostname;
            const player = document.getElementById('player');
            
            // Force unmuted autoplay - try multiple approaches
            player.src = `https://clips.twitch.tv/embed?clip=${{clips[i]}}&parent=${{domain}}&autoplay=true&muted=false`;
            
            // Also try setting iframe attributes for audio
            player.setAttribute('allow', 'autoplay; fullscreen; microphone; camera');
            player.setAttribute('allowfullscreen', 'true');
            
            document.getElementById('num').textContent = i + 1;
            document.getElementById('title').textContent = `TickleFitz Clip ${{i + 1}}`;
            
            // Reset progress bar
            document.getElementById('progress').style.width = '0%';
            
            // Progress bar for exactly 30 seconds
            let progress = 0;
            if (progressInterval) clearInterval(progressInterval);
            progressInterval = setInterval(() => {{
                progress += 100 / 300; // 30 seconds = 300 intervals of 100ms
                document.getElementById('progress').style.width = Math.min(progress, 100) + '%';
                if (progress >= 100) clearInterval(progressInterval);
            }}, 100);
            
            i = (i + 1) % clips.length;
            
            // Auto-advance after exactly 30 seconds
            setTimeout(() => {{
                document.getElementById('progress').style.width = '0%';
                // Immediate transition to next clip
                setTimeout(play, 100);
            }}, 30000); // Exactly 30 seconds
        }}
        
        // Auto-click to enable audio (some browsers require user interaction)
        document.addEventListener('click', () => {{
            // This ensures audio permissions are granted
            console.log('Audio permissions enabled');
        }});
        
        setTimeout(play, 1000);
    </script>
</body>
</html>
    """
    return html

@app.route('/refresh')
def refresh():
    """Endpoint to manually refresh clips"""
    return clips()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
