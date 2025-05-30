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
    
    return clips_data

@app.route('/')
def clips():
    try:
        clips_data = get_ticklefitz_clips()
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
        #twitch-embed { width: 100%; height: 100%; }
        .info { position: absolute; bottom: 20px; left: 20px; background: rgba(0,0,0,0.8); padding: 15px; border-radius: 10px; border-left: 4px solid #9146ff; z-index: 100; }
        .progress { position: absolute; bottom: 0; left: 0; height: 4px; background: #9146ff; transition: width 0.1s; z-index: 100; }
    </style>
    <!-- Load Twitch Embed JavaScript API -->
    <script src="https://embed.twitch.tv/embed/v1.js"></script>
</head>
<body>
    <div class="container">
        <div id="twitch-embed"></div>
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
        let embed = null;
        let player = null;
        let progressTimer = null;
        
        // Get the current hostname for parent parameter
        const parentDomain = window.location.hostname;
        console.log('Using parent domain:', parentDomain);
        
        function initializeTwitchEmbed() {
            console.log('Initializing Twitch Embed...');
            
            embed = new Twitch.Embed("twitch-embed", {
                width: "100%",
                height: "100%",
                autoplay: true,
                muted: false,
                parent: ["tf-clips-987c7b7b6cb8.herokuapp.com", "classic.golightstream.com"],
                layout: "video"
            });
            
            // Wait for embed to be ready
            embed.addEventListener(Twitch.Embed.VIDEO_READY, () => {
                console.log('Twitch embed ready');
                player = embed.getPlayer();
                
                // Set up player event listeners
                player.addEventListener(Twitch.Player.READY, onPlayerReady);
                player.addEventListener(Twitch.Player.ENDED, onVideoEnd);
                player.addEventListener(Twitch.Player.PLAY, onVideoPlay);
                player.addEventListener(Twitch.Player.PAUSE, onVideoPause);
                
                // Start playing first clip
                loadClip(currentIndex);
            });
        }
        
        function onPlayerReady() {
            console.log('Player is ready');
            // Try to unmute
            player.setMuted(false);
            player.setVolume(1.0);
        }
        
        function onVideoEnd() {
            console.log('Video ended, loading next clip...');
            currentIndex = (currentIndex + 1) % clips.length;
            setTimeout(() => loadClip(currentIndex), 1000);
        }
        
        function onVideoPlay() {
            console.log('Video started playing');
            // Try to unmute when video starts
            player.setMuted(false);
        }
        
        function onVideoPause() {
            console.log('Video paused');
        }
        
        function loadClip(index) {
            if (!player || clips.length === 0) return;
            
            const clip = clips[index];
            console.log(`Loading clip ${index + 1}: ${clip.title}`);
            
            // Update UI
            document.getElementById('title').textContent = clip.title;
            document.getElementById('num').textContent = index + 1;
            document.getElementById('details').textContent = `👁️ ${clip.view_count.toLocaleString()} views • 👤 ${clip.creator_name}`;
            
            // Reset progress bar
            document.getElementById('progress').style.width = '0%';
            
            // Load the clip in the player
            player.setClip(clip.id);
            
            // Start progress simulation (since we can't get exact duration easily)
            startProgressBar(clip.duration);
        }
        
        function startProgressBar(duration) {
            if (progressTimer) clearInterval(progressTimer);
            
            let progress = 0;
            const increment = 100 / (duration * 10); // Update every 100ms
            
            progressTimer = setInterval(() => {
                progress += increment;
                document.getElementById('progress').style.width = Math.min(progress, 100) + '%';
                
                if (progress >= 100) {
                    clearInterval(progressTimer);
                }
            }, 100);
        }
        
        // Manual click to enable audio
        document.addEventListener('click', () => {
            if (player) {
                player.setMuted(false);
                console.log('Manual unmute attempt');
            }
        });
        
        // Initialize when page loads
        window.addEventListener('load', () => {
            console.log(`Loaded ${clips.length} TickleFitz clips`);
            setTimeout(initializeTwitchEmbed, 1000);
        });
    </script>
</body>
</html>'''
    
    return html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
