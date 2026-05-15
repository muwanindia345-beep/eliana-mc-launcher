import subprocess
import threading
import os
import json
import time
import urllib.request
from flask import Flask, send_from_directory, jsonify

app = Flask(__name__)

# ── State files init ──────────────────────────────────────────
for state_file in ['gen_state.json', 'trf_state.json']:
    if not os.path.exists(state_file):
        with open(state_file, 'w') as f:
            json.dump({}, f)

# ── Routes ────────────────────────────────────────────────────
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

# ── Bot runner with auto-restart ──────────────────────────────
def run_bot(bot_file, label):
    base = os.path.dirname(os.path.abspath(__file__))
    while True:
        print(f"🚀 Starting {label}...")
        try:
            proc = subprocess.Popen(
                ['python', bot_file],
                cwd=base
            )
            proc.wait()  # wait for exit
            print(f"⚠️ {label} crashed or stopped! Restarting in 5s...")
        except Exception as e:
            print(f"❌ {label} error: {e}")
        time.sleep(5)

# ── Keep-alive ping ───────────────────────────────────────────
def keep_alive():
    PING_URL = os.environ.get(
        'RENDER_EXTERNAL_URL',
        'https://power-grid-empire.onrender.com'  # fix typo here if needed
    )
    time.sleep(10)  # wait for server to start
    while True:
        try:
            urllib.request.urlopen(PING_URL, timeout=10)
            print("💓 keep-alive ping sent!")
        except Exception as e:
            print(f"⚠️ keep-alive failed: {e}")
        time.sleep(270)

# ── Entry point ───────────────────────────────────────────────
if __name__ == '__main__':
    bots = [
        ('generator_bot.py',   '✅ generator_bot'),
        ('transformer_bot.py', '✅ transformer_bot'),
        ('satellite_bot.py',   '🛰️  satellite_bot'),
    ]

    for bot_file, label in bots:
        if os.path.exists(bot_file):
            t = threading.Thread(
                target=run_bot,
                args=(bot_file, label),
                daemon=True
            )
            t.start()
            print(f"{label} thread started!")
        else:
            print(f"⚠️ {bot_file} not found, skipped!")

    t_alive = threading.Thread(target=keep_alive, daemon=True)
    t_alive.start()
    print("💓 keep-alive thread started!")

    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
