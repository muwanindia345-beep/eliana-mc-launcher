import asyncio
import threading
import os
from flask import Flask, send_from_directory, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return send_from_directory('.', 'generator31.html')

@app.route('/<path:filename>')
def serve_file(filename):
    return send_from_directory('.', filename)

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

async def main():
    # Flask thread
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("✅ Web server started!")

    # Dono bots import karo
    import generator_bot
    import transformer_bot

    await asyncio.gather(
        generator_bot.client.start(os.getenv('BOT_TOKEN')),
        transformer_bot.client.start(os.getenv('BOT_TOKEN'))
    )

asyncio.run(main())
