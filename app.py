import os
import vlc
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return jsonify({'name': 'Performance Manager Remote Player', 'status': 'running', 'endpoints': ['/play', '/pause', '/stop', '/status', '/health']})

# Global player instance
class Player:
    def __init__(self):
        self.instance = vlc.Instance('--no-xlib --quiet')
        self.player = self.instance.media_player_new()
        self.current_url = None

    def play(self, url):
        if url != self.current_url:
            self.current_url = url
            media = self.instance.media_new(url)
            self.player.set_media(media)
        
        self.player.play()
        return self.get_status()

    def pause(self):
        self.player.pause()
        return self.get_status()

    def stop(self):
        self.player.stop()
        self.current_url = None
        return self.get_status()

    def set_volume(self, volume):
        # VLC volume is 0-100
        self.player.audio_set_volume(int(volume))
        return self.get_status()

    def seek(self, time_sec):
        # VLC seek is in ms
        self.player.set_time(int(time_sec * 1000))
        return self.get_status()

    def get_status(self):
        state = self.player.get_state()
        return {
            'is_playing': state == vlc.State.Playing,
            'state': str(state),
            'volume': self.player.audio_get_volume(),
            'time': self.player.get_time() / 1000, # Convert ms to sec
            'length': self.player.get_length() / 1000,
            'current_url': self.current_url
        }

player = Player()

@app.route('/play', methods=['POST'])
def play():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    status = player.play(url)
    return jsonify(status)

@app.route('/pause', methods=['POST'])
def pause():
    status = player.pause()
    return jsonify(status)

@app.route('/stop', methods=['POST'])
def stop():
    status = player.stop()
    return jsonify(status)

@app.route('/volume', methods=['POST'])
def volume():
    data = request.json
    level = data.get('level')
    if level is None:
        return jsonify({'error': 'Level is required'}), 400
    
    status = player.set_volume(level)
    return jsonify(status)

@app.route('/status', methods=['GET'])
def status():
    return jsonify(player.get_status())

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    print("Starting Remote Player Service on port 5001...")
    # Setup for headless audio if needed (env vars usually handle this for ALSA/Pulse)
    app.run(host='0.0.0.0', port=5001)
