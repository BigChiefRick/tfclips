from flask import Flask
import os
import requests
from datetime import datetime, timedelta
import json

app = Flask(__name__)

CLIENT_ID = os.environ.get('TWITCH_CLIENT_ID')
CLIENT_SECRET = os.environ.get('TWITCH_CLIENT_SECRET')

def get_ticklefitz_top_clips():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise Exception("Missing Twitch API credentials")
    
    # Get access token
    token_response = requests.post('https://id.twitch.tv/oauth2/token', {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials'
    })
    
    token = token_response.json()['access_token']
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {token}'
    }
    
    # Get TickleFitz user ID
    user_response = requests.get('https://api.twitch.tv/helix/users?login=ticklefitz', headers=headers)
    user_id = user_response.json()['data'][0]['id']
    
    # Get clips from last 30 days
    start_time = (datetime.now() - timedelta(days=30)).isoformat() + 'Z'
    clips_response = requests.get('https://api.twitch.tv/helix/clips', {
        'broadcaster_id': user_id,
        'first': 20,
        'started_at': start_time
    }, headers=headers)
    
    clips = clips_response.json()['data']
    
    # Sort by view count
    clips.sort(key=lambda x: x['view_count'], reverse=True)
    
    return clips

@app.route('/')
def player():
    try:
        clips = get_ticklefitz_top_clips()
    except:
        clips = []
    
    clips_json = json.dumps(clips)
    
    html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ margin: 0; background: #000; color: #fff; font-family: Arial; overflow: hidden; }}
        .container {{ width: 100vw; height: 100vh; position: relative; }}
        iframe {{ width: 100%; height: 100%; border: none; }}
        .info {{ position: absolute; bottom: 20px; left: 20px; background: rgba(0,0,0,0.8); padding: 15px; border-radius: 10px; }}
        .unmute-btn {{ position: absolute; top: -1000px; left: -1000px; opacity: 0; }}
    </style>
</head>
<body>
    <div class="container">
        <button id="unmuteBtn" class="unmute-btn">Unmute</button>
        <iframe id="player"></iframe>
        <div class="info">
            <div id="title">TickleFitz Clips</div>
            <div>Clip <span id="num">1</span> of {len(clips)}</div>
        </div>
    </div>
    <script>
        const clips = {clips_json};
        let index = 0;
        let audioUnlocked = false;
        
        function unlockAudio() {{
            if (!audioUnlocked) {{
                console.log('Auto-clicking to unlock audio...');
                
                // Multiple unlock attempts
                document.getElementById('unmuteBtn').click();
                
                // Create and dispatch multiple click events
                const clickEvent = new MouseEvent('click', {{
                    view: window,
                    bubbles: true,
                    cancelable: true
                }});
                document.body.dispatchEvent(clickEvent);
                
                // Touch event for mobile
                const touchEvent = new TouchEvent('touchstart', {{
                    bubbles: true,
                    cancelable: true
                }});
                document.body.dispatchEvent(touchEvent);
                
                // Try to unlock AudioContext
                if (window.AudioContext || window.webkitAudioContext) {{
                    const AudioContext = window.AudioContext || window.webkitAudioContext;
                    const ctx = new AudioContext();
                    if (ctx.state === 'suspended') {{
                        ctx.resume().then(() => {{
                            console.log('AudioContext resumed');
                        }});
                    }}
                }}
                
                audioUnlocked = true;
                console.log('Audio unlocked for all clips');
            }}
        }}
        
        function playClip() {{
            if (clips.length === 0) return;
            
            const clip = clips[index];
            const embedUrl = `https://clips.twitch.tv/embed?clip=${{clip.id}}&parent=tf-clips-987c7b7b6cb8.herokuapp.com&parent=classic.golightstream.com&autoplay=true&muted=false&volume=1`;
            
            const player = document.getElementById('player');
            player.src = embedUrl;
            
            // Try to send unmute message to iframe after it loads
            player.onload = function() {{
                setTimeout(() => {{
                    try {{
                        // Try multiple unmute methods
                        player.contentWindow.postMessage('{{"event":"command","func":"unMute","args":[]}}', '*');
                        player.contentWindow.postMessage('{{"event":"command","func":"setVolume","args":[1]}}', '*');
                        player.contentWindow.postMessage('unmute', '*');
                        console.log('Sent unmute commands to iframe');
                    }} catch (e) {{
                        console.log('Could not send unmute commands:', e);
                    }}
                }}, 2000);
            }};
            
            document.getElementById('title').textContent = clip.title;
            document.getElementById('num').textContent = index + 1;
            
            console.log(`Playing: ${{clip.title}} (${{clip.view_count}} views)`);
            
            index = (index + 1) % clips.length;
            setTimeout(playClip, clip.duration * 1000 + 2000);
        }}
        
        // Auto-unlock audio then start playing
        setTimeout(() => {{
            unlockAudio();
            setTimeout(playClip, 500);
        }}, 1000);
    </script>
</body>
</html>
    '''
    
    return html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
