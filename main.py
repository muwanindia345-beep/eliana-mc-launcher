import subprocess
import threading
import os
import json
import urllib.request
from flask import Flask, send_from_directory, jsonify

app = Flask(__name__)

# ── Fix missing state files ──
for state_file in ['gen_state.json', 'trf_state.json']:
    if not os.path.exists(state_file):
        with open(state_file, 'w') as f:
            json.dump({}, f)

@app.route('/')
def index():
    return send_from_directory('.', 'generator31.html')

@app.route('/gen_state.json')
def gen_state():
    try:
        return send_from_directory('.', 'gen_state.json')
    except:
        return jsonify({})

@app.route('/trf_state.json')
def trf_state():
    try:
        return send_from_directory('.', 'trf_state.json')
    except:
        return jsonify({})

@app.route('/<path:filename>')
def serve_file(filename):
    try:
        return send_from_directory('.', filename)
    except:
        return "Not found", 404

def run_bot(bot_file):
    base = os.path.dirname(os.path.abspath(__file__))
    subprocess.run(['python', bot_file], cwd=base)

# ── Keep Render awake ──
def keep_alive():
    import time
    time.sleep(30)
    while True:
        try:
            # External URL ping — Render ko jaagta rakhta hai
            urllib.request.urlopen('https://powe-grid-empire.onrender.com')
            print("💓 Keep-alive ping sent!")
        except Exception as e:
            print(f"⚠️ Keep-alive: {e}")
        time.sleep(270)  # Har 4.5 min

if __name__ == '__main__':
    # ── Start all bots ──
    bots = [
        ('generator_bot.py',   '✅ generator_bot'),
        ('transformer_bot.py', '✅ transformer_bot'),
        ('satellite_bot.py',   '🛰️  satellite_bot'),
    ]

    for bot_file, label in bots:
        if os.path.exists(bot_file):
            t = threading.Thread(target=run_bot, args=[bot_file])
            t.daemon = True
            t.start()
            print(f"{label} — started!")
        else:
            print(f"⚠️ {bot_file} not found — skipped!")

    # ── Keep alive ──
    t_alive = threading.Thread(target=keep_alive)
    t_alive.daemon = True
    t_alive.start()
    print("💓 Keep-alive — started!")

    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

