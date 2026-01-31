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
class PlayerWrapper:
    def __init__(self, vlc_instance, url):
        self.player = vlc_instance.media_player_new()
        media = vlc_instance.media_new(url)
        self.player.set_media(media)
        self.player.audio_set_volume(100)
        self.url = url
        self.fading = False

    def play(self):
        self.player.play()

    def stop(self):
        self.fading = False # Stop fading if active
        self.player.stop()
    
    def set_volume(self, vol):
        self.player.audio_set_volume(int(vol))
    
    def get_volume(self):
        return self.player.audio_get_volume()
        
    def get_state(self):
        return self.player.get_state()
        
    def get_time(self):
        return self.player.get_time()
        
    def get_length(self):
        return self.player.get_length()

    def fade_volume(self, start_vol, end_vol, duration):
        def fade():
            self.fading = True
            steps = 20
            if duration <= 0: duration = 0.1
            step_time = duration / steps
            vol_step = (end_vol - start_vol) / steps
            current_vol = start_vol
            
            for _ in range(steps):
                if not self.fading: break
                current_vol += vol_step
                self.set_volume(current_vol)
                time.sleep(step_time)
            
            if self.fading:
                self.set_volume(end_vol)
                self.fading = False
                # If faded to 0, assume we should stop/release
                if end_vol == 0:
                    self.stop()

        threading.Thread(target=fade, daemon=True).start()

class PlayerManager:
    def __init__(self):
        self.instance = vlc.Instance('--no-xlib --quiet')
        self.active_players = [] # List of PlayerWrapper
        self.current_player = None # The main player (newest)

    def play(self, url, crossfade=False):
        new_player = PlayerWrapper(self.instance, url)
        
        if crossfade and self.current_player and self.current_player.get_state() in [vlc.State.Playing, vlc.State.Buffering]:
            # Crossfade logic
            print(f"Crossfading to {url}")
            
            # Fade out old current player
            self.current_player.fade_volume(self.current_player.get_volume(), 0, 10)
            
            # Fade in new player
            new_player.set_volume(0)
            new_player.play()
            new_player.fade_volume(0, 100, 5)
            
            self.active_players.append(new_player)
            self.current_player = new_player
            
            # Cleanup old players from list (simple cleanup)
            self.cleanup_stopped_players()
        else:
            # Hard stop/replace
            print(f"Playing {url}")
            self.stop()
            new_player.play()
            self.active_players.append(new_player)
            self.current_player = new_player
            
        return self.get_status()

    def pause(self):
        if self.current_player:
            self.current_player.player.pause()
        return self.get_status()

    def stop(self):
        for p in self.active_players:
            p.stop()
        self.active_players = []
        self.current_player = None
        return self.get_status()

    def set_volume(self, volume):
        if self.current_player:
            self.current_player.set_volume(volume)
        return self.get_status()

    def seek(self, time_sec):
        if self.current_player:
            self.current_player.player.set_time(int(time_sec * 1000))
        return self.get_status()
        
    def cleanup_stopped_players(self):
        # Remove players that are stopped or invalid
        # This is a basic cleanup to prevent memory leaks in long sessions
        active = []
        for p in self.active_players:
            state = p.get_state()
            if state not in [vlc.State.Ended, vlc.State.Error, vlc.State.Stopped] or p == self.current_player:
                active.append(p)
        self.active_players = active

    def get_status(self):
        if not self.current_player:
            return {
                'is_playing': False,
                'state': 'Stopped',
                'volume': 0,
                'time': 0,
                'length': 0,
                'current_url': None
            }
            
        state = self.current_player.get_state()
        return {
            'is_playing': state == vlc.State.Playing,
            'state': str(state),
            'volume': self.current_player.get_volume(),
            'time': self.current_player.get_time() / 1000,
            'length': self.current_player.get_length() / 1000,
            'current_url': self.current_player.url
        }

player = PlayerManager()

@app.route('/play', methods=['POST'])
def play():
    data = request.json
    url = data.get('url')
    crossfade = data.get('crossfade', False)
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    status = player.play(url, crossfade)
    return jsonify(status)

@app.route('/pause', methods=['POST'])
def pause():
    status = player.pause()
    return jsonify(status)

@app.route('/stop', methods=['POST'])
def stop():
    status = player.stop()
    return jsonify(status)

@app.route('/seek', methods=['POST'])
def seek():
    data = request.json
    time = data.get('time')
    if time is None:
        return jsonify({'error': 'Time is required'}), 400
    
    status = player.seek(time)
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
