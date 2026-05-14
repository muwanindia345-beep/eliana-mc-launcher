import subprocess
import threading
import os
from flask import Flask, send_from_directory

app = Flask(__name__)

@app.route('/')
def index():
    return send_from_directory('.', 'generator31.html')

@app.route('/<path:filename>')
def serve_file(filename):
    try:
        return send_from_directory('.', filename)
    except:
        return "Not found", 404

def run_bot(bot_file):
    subprocess.run(['python', bot_file], cwd='/app')

if __name__ == '__main__':
    # Dono bots alag threads mein chalao
    t1 = threading.Thread(target=run_bot, args=['generator_bot.py'])
    t2 = threading.Thread(target=run_bot, args=['transformer_bot.py'])
    t3 = threading.Thread(target=run_bot, args=['satellite_bot.py'])
    t1.daemon = True
    t2.daemon = True
    t3.daemon = True
    t1.start()
    t2.start()
    t3.start()
    print("✅ All 3 bots started!")

    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
