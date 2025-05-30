from flask import Flask
import os
import requests
import json
import subprocess
import tempfile
import re
from datetime import datetime, timedelta

app = Flask(__name__)

# Environment variables needed
CLIENT_ID = os.environ.get('TWITCH_CLIENT_ID')
CLIENT_SECRET = os.environ.get('TWITCH_CLIENT_SECRET')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_REPO = os.environ.get('GITHUB_REPO')  # format: "username/repo-name"

class ClipManager:
    def __init__(self):
        self.clips_data = []
        
    def get_twitch_clips(self):
        """Get top TickleFitz clips from Twitch API"""
        try:
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
            clips.sort(key=lambda x: x['view_count'], reverse=True)
            
            self.clips_data = clips[:10]  # Top 10 clips to keep file sizes manageable
            return True
            
        except Exception as e:
            print(f"Error fetching clips: {e}")
            return False
    
    def extract_mp4_url(self, thumbnail_url):
        """Extract MP4 URL from thumbnail URL"""
        # Try different patterns for Twitch CDN
        patterns = [
            r'(https://static-cdn\.jtvnw\.net/twitch-clips/[^/]+/[^-]+-offset-\d+)-preview-\d+x\d+\.jpg',
            r'(https://clips-media-assets2\.twitch\.tv/.*)-preview',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, thumbnail_url)
            if match:
                return match.group(1) + '.mp4'
        return None
    
    def download_clip(self, clip_id, mp4_url, filename):
        """Download a clip MP4 file"""
        try:
            response = requests.get(mp4_url, stream=True, timeout=30)
            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            return False
        except:
            return False
    
    def update_github_repo(self):
        """Download clips and update GitHub repo"""
        if not GITHUB_TOKEN or not GITHUB_REPO:
            return False
            
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Clone repo
                repo_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
                subprocess.run(['git', 'clone', repo_url, temp_dir], check=True, capture_output=True)
                
                os.chdir(temp_dir)
                
                # Create clips directory
                clips_dir = 'clips'
                os.makedirs(clips_dir, exist_ok=True)
                
                successful_clips = []
                
                # Download each clip
                for i, clip in enumerate(self.clips_data):
                    mp4_url = self.extract_mp4_url(clip['thumbnail_url'])
                    if mp4_url:
                        filename = f"{clips_dir}/clip_{i+1}_{clip['id']}.mp4"
                        if self.download_clip(clip['id'], mp4_url, filename):
                            successful_clips.append({
                                'id': clip['id'],
                                'title': clip['title'],
                                'filename': filename,
                                'view_count': clip['view_count'],
                                'duration': clip['duration'],
                                'creator_name': clip['creator_name']
                            })
                            print(f"Downloaded: {clip['title']}")
                
                # Create clips manifest
                with open('clips/manifest.json', 'w') as f:
                    json.dump(successful_clips, f, indent=2)
                
                # Commit and push
                subprocess.run(['git', 'add', '.'], check=True)
                subprocess.run(['git', 'config', 'user.email', 'action@github.com'], check=True)
                subprocess.run(['git', 'config', 'user.name', 'Clips Bot'], check=True)
                subprocess.run(['git', 'commit', '-m', f'Update clips - {datetime.now().strftime("%Y-%m-%d %H:%M")}'], check=True)
                subprocess.run(['git', 'push'], check=True)
                
                return len(successful_clips)
                
        except Exception as e:
            print(f"GitHub update error: {e}")
            return False

clip_manager = ClipManager()

@app.route('/')
def player():
    """Main clips player page"""
    
    # Try to get clips manifest from GitHub
    try:
        manifest_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/clips/manifest.json"
        response = requests.get(manifest_url)
        if response.status_code == 200:
            clips = response.json()
        else:
            clips = []
    except:
        clips = []
    
    if not clips:
        return '''
        <html>
        <body style="background:#000;color:#fff;font-family:Arial;text-align:center;padding:50px;">
            <h1>🎮 TickleFitz Clips Player</h1>
            <p>No clips available yet. <a href="/update" style="color:#00d4ff;">Click here to fetch clips</a></p>
        </body>
        </html>
        '''
    
    clips_json = json.dumps(clips)
    base_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/"
    
    html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ margin: 0; background: #000; color: #fff; font-family: Arial; overflow: hidden; }}
        .container {{ width: 100vw; height: 100vh; position: relative; }}
        video {{ width: 100%; height: 100%; object-fit: cover; }}
        .info {{ 
            position: absolute; bottom: 20px; left: 20px; 
            background: rgba(0,0,0,0.8); padding: 15px; 
            border-radius: 10px; border-left: 4px solid #9146ff; 
        }}
        .loading {{ 
            position: absolute; top: 50%; left: 50%; 
            transform: translate(-50%, -50%); text-align: center; 
        }}
    </style>
</head>
<body>
    <div class="container">
        <video id="player" autoplay muted></video>
        <div class="info">
            <div id="title">TickleFitz Clips</div>
            <div>Clip <span id="num">1</span> of {len(clips)}</div>
            <div id="details" style="font-size:12px;color:#ccc;margin-top:5px;"></div>
        </div>
    </div>
    <script>
        const clips = {clips_json};
        const baseUrl = "{base_url}";
        let currentIndex = 0;
        const player = document.getElementById('player');
        
        // Unmute on first user interaction
        document.addEventListener('click', () => {{
            player.muted = false;
            console.log('Audio enabled');
        }});
        
        // Auto-unmute attempt
        setTimeout(() => {{
            player.muted = false;
        }}, 2000);
        
        function playClip() {{
            if (clips.length === 0) return;
            
            const clip = clips[currentIndex];
            const videoUrl = baseUrl + clip.filename;
            
            player.src = videoUrl;
            
            document.getElementById('title').textContent = clip.title;
            document.getElementById('num').textContent = currentIndex + 1;
            document.getElementById('details').textContent = `Views: ${{clip.view_count.toLocaleString()}} | Creator: ${{clip.creator_name}}`;
            
            console.log(`Playing: ${{clip.title}} from GitHub`);
            
            currentIndex = (currentIndex + 1) % clips.length;
        }}
        
        // Auto-advance when video ends
        player.addEventListener('ended', () => {{
            setTimeout(playClip, 1000);
        }});
        
        // Handle video errors
        player.addEventListener('error', () => {{
            console.log('Video error, trying next clip...');
            setTimeout(playClip, 2000);
        }});
        
        // Start playing
        setTimeout(playClip, 1000);
        
        console.log(`Loaded ${{clips.length}} clips from GitHub storage`);
    </script>
</body>
</html>
    '''
    
    return html

@app.route('/update')
def update_clips():
    """Manually trigger clips update"""
    
    if not CLIENT_ID or not CLIENT_SECRET:
        return "Missing Twitch API credentials"
    
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return "Missing GitHub configuration"
    
    print("Fetching TickleFitz clips...")
    if not clip_manager.get_twitch_clips():
        return "Failed to fetch clips from Twitch"
    
    print("Updating GitHub repo...")
    result = clip_manager.update_github_repo()
    
    if result:
        return f"✅ Successfully updated {result} clips! <a href='/'>View Player</a>"
    else:
        return "❌ Failed to update GitHub repo"

@app.route('/status')
def status():
    """Show current status"""
    try:
        manifest_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/clips/manifest.json"
        response = requests.get(manifest_url)
        if response.status_code == 200:
            clips = response.json()
            return f"📊 {len(clips)} clips available in GitHub storage"
        else:
            return "No clips found in GitHub"
    except:
        return "Error checking GitHub status"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
