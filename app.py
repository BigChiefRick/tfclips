from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def clips():
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { margin: 0; background: #000; color: #fff; font-family: Arial; overflow: hidden; }
        .container { width: 100vw; height: 100vh; position: relative; }
        iframe { width: 100%; height: 100%; border: none; }
        .info { 
            position: absolute; bottom: 20px; left: 20px; 
            background: rgba(0,0,0,0.8); padding: 15px; 
            border-radius: 10px; border-left: 4px solid #9146ff; 
        }
        .progress { 
            position: absolute; bottom: 0; left: 0; height: 4px; 
            background: #9146ff; transition: width 0.1s; 
        }
    </style>
</head>
<body>
    <div class="container">
        <iframe id="player"></iframe>
        <div class="info">
            <div id="title">TickleFitz Clips</div>
            <div>Clip <span id="num">1</span> of 10</div>
        </div>
        <div id="progress" class="progress" style="width: 0%;"></div>
    </div>
    <script>
        const clips = [
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
        ];
        let i = 0;
        let progressInterval;
        
        function play() {
            const domain = window.location.hostname;
            document.getElementById('player').src = `https://clips.twitch.tv/embed?clip=${clips[i]}&parent=${domain}&autoplay=true&muted=false`;
            document.getElementById('num').textContent = i + 1;
            document.getElementById('title').textContent = `TickleFitz Clip ${i + 1}`;
            
            // Progress bar
            let progress = 0;
            if (progressInterval) clearInterval(progressInterval);
            progressInterval = setInterval(() => {
                progress += 100 / 450; // 45 seconds = 450 intervals of 100ms
                document.getElementById('progress').style.width = Math.min(progress, 100) + '%';
                if (progress >= 100) clearInterval(progressInterval);
            }, 100);
            
            i = (i + 1) % clips.length;
            setTimeout(() => {
                document.getElementById('progress').style.width = '0%';
                setTimeout(play, 500);
            }, 45000);
        }
        
        setTimeout(play, 1000);
    </script>
</body>
</html>
    """
    return html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
