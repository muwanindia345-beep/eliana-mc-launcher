import asyncio
import threading
import os
from flask import Flask, send_from_directory
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.environ.get('BOT_TOKEN')

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

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

async def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    print("✅ Web server started!")

    from generator_bot  import client as gen_client,  on_ready as gen_ready
    from transformer_bot import client as trf_client, on_ready as trf_ready

    await asyncio.gather(
        gen_client.start(BOT_TOKEN),
        trf_client.start(BOT_TOKEN),
    )

asyncio.run(main())
