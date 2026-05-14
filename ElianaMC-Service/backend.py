from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess, asyncio, uvicorn, os, time

app = FastAPI(title="ElianaMC Service", version="1.0")

app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"],
    allow_headers=["*"], allow_credentials=True
)

MC  = {"proc": None, "type": "java"}
LOG = []
WS_CLIENTS = []
PLAYER_COUNT = {"count": 0}
LAST_ACTIVITY = {"time": 0}
NO_PLAYER_TIMEOUT = 1200

PROPS_PATH = {
    "java":    "/root/SeraphinaMC/server.properties",
    "bedrock": "/root/LuciaMC/server.properties"
}

class TypeModel(BaseModel):
    type: str

def is_running():
    if MC["proc"] and MC["proc"].poll() is None:
        return True
    cmd = ["pgrep", "-f", "paper.jar" if MC["type"] == "java" else "bedrock_server"]
    return subprocess.run(cmd, capture_output=True).returncode == 0

async def broadcast(msg: str, status: str = None):
    LOG.append(msg)
    if len(LOG) > 500: LOG.pop(0)
    m = msg.lower()
    if not status:
        if "done" in m and "for help" in m: status = "started"
        elif "server started" in m: status = "started"
        elif "stopping" in m or "server process ended" in m: status = "stopped"
    if "joined the game" in m:
        PLAYER_COUNT["count"] += 1
        LAST_ACTIVITY["time"] = time.time()
    elif "left the game" in m:
        PLAYER_COUNT["count"] = max(0, PLAYER_COUNT["count"] - 1)
        LAST_ACTIVITY["time"] = time.time()
    payload = {"type": "log", "message": msg}
    if status: payload["status"] = status
    dead = []
    for ws in WS_CLIENTS:
        try: await ws.send_json(payload)
        except: dead.append(ws)
    for d in dead: WS_CLIENTS.remove(d)

async def stream_output():
    while True:
        proc = MC["proc"]
        if proc and proc.stdout and proc.poll() is None:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, proc.stdout.readline)
                if line:
                    decoded = line.decode("utf-8", errors="ignore").strip()
                    if decoded: await broadcast(decoded)
                else:
                    await broadcast("[ElianaMC] Server process ended.", "stopped")
                    MC["proc"] = None
                    PLAYER_COUNT["count"] = 0
                    await asyncio.sleep(1)
            except Exception as e:
                await broadcast(f"[ERROR] {str(e)}")
                await asyncio.sleep(1)
        else:
            await asyncio.sleep(0.5)

async def auto_shutdown_task():
    while True:
        await asyncio.sleep(60)
        if not is_running(): continue
        if LAST_ACTIVITY["time"] > 0:
            elapsed = time.time() - LAST_ACTIVITY["time"]
            if elapsed > NO_PLAYER_TIMEOUT and PLAYER_COUNT["count"] == 0:
                await broadcast("[ElianaMC] No players — auto shutting down...")
                await stop_server()
                LAST_ACTIVITY["time"] = 0

@app.on_event("startup")
async def startup():
    asyncio.create_task(stream_output())
    asyncio.create_task(auto_shutdown_task())

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/status")
async def status():
    return {"status": "online" if is_running() else "offline", "type": MC["type"], "players": PLAYER_COUNT["count"]}

@app.get("/players")
async def players():
    return {"count": PLAYER_COUNT["count"]}

@app.post("/server-type")
async def set_type(data: TypeModel):
    MC["type"] = data.type
    return {"type": MC["type"]}

@app.get("/server-type")
async def get_type():
    return {"type": MC["type"]}

@app.post("/start")
async def start_server():
    if is_running():
        return {"status": "already_running"}
    try:
        env = {**os.environ, "TERM": "xterm"}
        eula_path = "/root/SeraphinaMC/eula.txt"
        with open(eula_path, "w") as f:
            f.write("eula=true\n")
        if MC["type"] == "java":
            proc = subprocess.Popen(
                ["java", "-Xmx2G", "-Xms1G", "-jar", "paper.jar", "nogui", "--port", "25566"],
                cwd="/root/SeraphinaMC",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env
            )
        else:
            proc = subprocess.Popen(
                ["stdbuf", "-oL", "-eL", "box64", "./bedrock_server"],
                cwd="/root/LuciaMC",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env
            )
        MC["proc"] = proc
        PLAYER_COUNT["count"] = 0
        LAST_ACTIVITY["time"] = time.time()
        await broadcast(f"[ElianaMC] {MC['type'].upper()} server starting...")
        return {"status": "starting", "type": MC["type"]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

async def stop_server():
    try:
        proc = MC["proc"]
        if proc and proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=10)
            except: proc.kill()
        MC["proc"] = None
        PLAYER_COUNT["count"] = 0
        cmd = "pkill -f paper.jar" if MC["type"] == "java" else "pkill -f bedrock_server"
        subprocess.run(cmd.split(), capture_output=True)
        await broadcast("[ElianaMC] Server stopped.", "stopped")
        return {"status": "stopped"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.post("/stop")
async def stop():
    return await stop_server()

@app.post("/restart")
async def restart():
    await stop_server()
    await asyncio.sleep(2)
    await start_server()
    return {"status": "restarting"}

@app.get("/logs")
async def get_logs():
    return {"logs": LOG}

@app.get("/properties")
async def get_properties(type: str = "java"):
    path = PROPS_PATH.get(type, PROPS_PATH["java"])
    props = {}
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    props[k.strip()] = v.strip()
        return {"success": True, "properties": props}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/properties")
async def save_properties(data: dict):
    stype = data.get("type", "java")
    props = data.get("properties", {})
    path  = PROPS_PATH.get(stype, PROPS_PATH["java"])
    try:
        with open(path, "r") as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k = stripped.split("=", 1)[0].strip()
                if k in props:
                    new_lines.append(f"{k}={props[k]}\n")
                    continue
            new_lines.append(line)
        with open(path, "w") as f:
            f.writelines(new_lines)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.websocket("/ws/console")
async def console_ws(websocket: WebSocket):
    await websocket.accept()
    WS_CLIENTS.append(websocket)
    for log in LOG[-100:]:
        await websocket.send_json({"type": "log", "message": log})
    try:
        while True:
            data = await websocket.receive_text()
            proc = MC["proc"]
            if proc and proc.stdin:
                try:
                    proc.stdin.write((data + "\n").encode())
                    proc.stdin.flush()
                except: pass
    except WebSocketDisconnect:
        if websocket in WS_CLIENTS: WS_CLIENTS.remove(websocket)
    except:
        if websocket in WS_CLIENTS: WS_CLIENTS.remove(websocket)

if __name__ == "__main__":
    uvicorn.run("backend:app", host="0.0.0.0", port=8007, reload=False)
