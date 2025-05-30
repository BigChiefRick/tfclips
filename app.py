import gradio as gr

def create_html():
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { margin: 0; background: #000; color: #fff; font-family: Arial; }
        .container { width: 100vw; height: 100vh; position: relative; }
        iframe { width: 100%; height: 100%; border: none; }
        .info { position: absolute; bottom: 20px; left: 20px; background: rgba(0,0,0,0.8); padding: 15px; border-radius: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <iframe id="player"></iframe>
        <div class="info">
            <div id="title">TickleFitz Clip Playing</div>
            <div>Clip <span id="num">1</span> of 5</div>
        </div>
    </div>
    <script>
        const clips = [
            'AwkwardHelplessSalamanderSwiftRage',
            'TameIntelligentChimpanzeeHassaanChop', 
            'PowerfulHandsomeNarwhalM4xHeh',
            'GloriousEagerDogePogChamp',
            'InventiveRealTapirCorgiDerp'
        ];
        let i = 0;
        function play() {
            document.getElementById('player').src = `https://clips.twitch.tv/embed?clip=${clips[i]}&parent=huggingface.co&autoplay=true`;
            document.getElementById('num').textContent = i + 1;
            i = (i + 1) % clips.length;
            setTimeout(play, 45000);
        }
        setTimeout(play, 1000);
    </script>
</body>
</html>
    """

with gr.Blocks() as demo:
    gr.HTML(create_html())

demo.launch()
