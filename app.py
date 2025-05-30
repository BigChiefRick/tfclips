import os
import requests
from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Twitch API configuration
CLIENT_ID = os.environ.get('TWITCH_CLIENT_ID', '')
CLIENT_SECRET = os.environ.get('TWITCH_CLIENT_SECRET', '')
BROADCASTER_NAME = 'ticklefitz'

class TwitchAPI:
    def __init__(self):
        self.access_token = None
        self.token_expires = None
    
    def get_access_token(self):
        """Get OAuth token for Twitch API"""
        if self.access_token and self.token_expires and datetime.now() < self.token_expires:
            return self.access_token
        
        url = 'https://id.twitch.tv/oauth2/token'
        params = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'client_credentials'
        }
        
        try:
            response = requests.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            self.access_token = data['access_token']
            # Set token to expire 1 hour before actual expiry for safety
            self.token_expires = datetime.now() + timedelta(seconds=data['expires_in'] - 3600)
            
            return self.access_token
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            return None
    
    def get_user_id(self, username):
        """Get user ID from username"""
        token = self.get_access_token()
        if not token:
            return None
        
        headers = {
            'Client-ID': CLIENT_ID,
            'Authorization': f'Bearer {token}'
        }
        
        url = 'https://api.twitch.tv/helix/users'
        params = {'login': username}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data['data']:
                return data['data'][0]['id']
            return None
        except Exception as e:
            logger.error(f"Failed to get user ID: {e}")
            return None
    
    def get_clips(self, broadcaster_id, count=10, period='week'):
        """Get clips for a broadcaster"""
        token = self.get_access_token()
        if not token:
            return []
        
        headers = {
            'Client-ID': CLIENT_ID,
            'Authorization': f'Bearer {token}'
        }
        
        # Calculate date range based on period
        end_time = datetime.now()
        if period == 'day':
            start_time = end_time - timedelta(days=1)
        elif period == 'week':
            start_time = end_time - timedelta(weeks=1)
        elif period == 'month':
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(weeks=1)
        
        url = 'https://api.twitch.tv/helix/clips'
        params = {
            'broadcaster_id': broadcaster_id,
            'first': min(count, 100),  # Twitch API limit
            'started_at': start_time.isoformat() + 'Z',
            'ended_at': end_time.isoformat() + 'Z'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            clips = []
            for clip in data.get('data', []):
                clips.append({
                    'id': clip['id'],
                    'slug': clip['id'],  # In newer API, id is used as slug
                    'title': clip['title'],
                    'creator_name': clip['creator_name'],
                    'view_count': clip['view_count'],
                    'created_at': clip['created_at'],
                    'thumbnail_url': clip['thumbnail_url'],
                    'duration': clip['duration'],
                    'embed_url': f"https://clips.twitch.tv/embed?clip={clip['id']}&parent=herokuapp.com&autoplay=false&muted=false"
                })
            
            # Sort by view count descending
            clips.sort(key=lambda x: x['view_count'], reverse=True)
            return clips[:count]
            
        except Exception as e:
            logger.error(f"Failed to get clips: {e}")
            return []

# Initialize Twitch API
twitch_api = TwitchAPI()

@app.route('/')
def index():
    """Main page showing clips"""
    count = request.args.get('count', 10, type=int)
    period = request.args.get('period', 'week')
    autoplay = request.args.get('autoplay', 'false').lower() == 'true'
    
    # Limit count to reasonable range
    count = max(1, min(count, 50))
    
    return render_template('index.html', 
                         broadcaster_name=BROADCASTER_NAME,
                         count=count, 
                         period=period,
                         autoplay=autoplay)

@app.route('/api/clips')
def api_clips():
    """API endpoint to get clips data"""
    count = request.args.get('count', 10, type=int)
    period = request.args.get('period', 'week')
    
    # Limit count to reasonable range
    count = max(1, min(count, 50))
    
    # Get broadcaster ID
    broadcaster_id = twitch_api.get_user_id(BROADCASTER_NAME)
    if not broadcaster_id:
        return jsonify({'error': 'Failed to get broadcaster ID'}), 500
    
    # Get clips
    clips = twitch_api.get_clips(broadcaster_id, count, period)
    
    return jsonify({
        'clips': clips,
        'broadcaster_name': BROADCASTER_NAME,
        'count': len(clips),
        'period': period
    })

@app.route('/stream')
def stream_view():
    """Stream-friendly view for OBS/streaming software"""
    count = request.args.get('count', 5, type=int)
    period = request.args.get('period', 'week')
    interval = request.args.get('interval', 30, type=int)  # seconds between clips
    
    count = max(1, min(count, 20))
    interval = max(10, min(interval, 300))  # 10 seconds to 5 minutes
    
    return render_template('stream.html',
                         broadcaster_name=BROADCASTER_NAME,
                         count=count,
                         period=period,
                         interval=interval)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    # Check if required environment variables are set
    if not CLIENT_ID or not CLIENT_SECRET:
        logger.warning("TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET environment variables are required")
        logger.warning("The app will not function properly without these credentials")
    
    port = int(os.environ.get('PORT', 5000))  # Default port for Heroku
    app.run(host='0.0.0.0', port=port, debug=False)
