import subprocess
import threading
import os
import json
import urllib.request
from flask import Flask, send_from_directory, jsonify

app = Flask(__name__)

# ── Fix gen_state.json 404 error ──
if not os.path.exists('gen_state.json'):
    with open('gen_state.json', 'w') as f:
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
            port = os.environ.get('PORT', '8080')
            urllib.request.urlopen(f'http://localhost:{port}')
            print("💓 Keep-alive ping sent")
        except Exception as e:
            print(f"⚠️ Keep-alive: {e}")
        time.sleep(270)

if __name__ == '__main__':
    # ── Start all 3 bots ──
    t1 = threading.Thread(target=run_bot, args=['generator_bot.py'])
    t2 = threading.Thread(target=run_bot, args=['transformer_bot.py'])
    t3 = threading.Thread(target=run_bot, args=['satellite_bot.py'])
    t1.daemon = True
    t2.daemon = True
    t3.daemon = True
    t1.start()
    t2.start()
    t3.start()
    print("✅ generator_bot   — started!")
    print("✅ transformer_bot — started!")
    print("🛰️  satellite_bot  — started!")

    # ── Keep alive ──
    t_alive = threading.Thread(target=keep_alive)
    t_alive.daemon = True
    t_alive.start()
    print("💓 Keep-alive     — started!")

    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

