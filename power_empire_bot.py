import subprocess, threading, os, json, urllib.request
from flask import Flask, send_from_directory, jsonify

app = Flask(__name__)

for f in ['gen_state.json','trf_state.json']:
    if not os.path.exists(f):
        with open(f,'w') as fp: json.dump({},fp)

@app.route('/')
def index(): return send_from_directory('.','generator31.html')

@app.route('/<path:filename>')
def serve(filename):
    try: return send_from_directory('.',filename)
    except: return "Not found",404

def run_bot():
    import subprocess,os
    subprocess.run(['python','power_empire_bot.py'],
                   cwd=os.path.dirname(os.path.abspath(__file__)))

def keep_alive():
    import time; time.sleep(30)
    while True:
        try: urllib.request.urlopen('https://powe-grid-empire.onrender.com')
        except: pass
        time.sleep(270)

if __name__=='__main__':
    threading.Thread(target=run_bot,daemon=True).start()
    print("✅ Power Empire Bot started!")
    threading.Thread(target=keep_alive,daemon=True).start()
    print("💓 Keep-alive started!")
    port=int(os.environ.get('PORT',8080))
    app.run(host='0.0.0.0',port=port,debug=False)
