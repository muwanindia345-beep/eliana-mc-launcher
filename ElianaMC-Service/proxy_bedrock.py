import asyncio
import httpx
import time
import socket

PROXY_HOST   = "0.0.0.0"
PROXY_PORT   = 19132
MC_HOST      = "127.0.0.1"
MC_PORT      = 19135
BACKEND      = "http://localhost:8007"

# ── RakNet UNCONNECTED_PING header ────────────────
UNCONNECTED_PING    = b'\x01'
UNCONNECTED_PONG    = b'\x1c'
OFFLINE_MSG         = b'\x00\xff\xff\x00\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x12\x34\x56\x78'

# ── Helpers ───────────────────────────────────────
async def is_online():
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{BACKEND}/status", timeout=2)
            return r.json().get("status") == "online"
    except:
        return False

async def start_server():
    try:
        async with httpx.AsyncClient() as c:
            await c.post(f"{BACKEND}/start", timeout=2)
    except:
        pass

async def wait_until_online(timeout=180):
    start = time.time()
    while time.time() - start < timeout:
        if await is_online():
            return True
        await asyncio.sleep(3)
    return False

# ── Build PONG packet ─────────────────────────────
def make_pong(ping_data, status="Starting..."):
    motd = f"MCPE;{status};390;1.14.0;0;10;12345678;ElianaMC;Survival;1;{MC_PORT};"
    motd_bytes = motd.encode("utf-8")

    pong = bytearray()
    pong += UNCONNECTED_PONG
    pong += ping_data[1:9]          # Ping time
    pong += b'\x00' * 8             # Server GUID
    pong += OFFLINE_MSG
    pong += len(motd_bytes).to_bytes(2, 'big')
    pong += motd_bytes
    return bytes(pong)

# ── UDP Protocol ──────────────────────────────────
class BedrockProxy(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport    = None
        self.clients      = {}
        self.starting     = False
        self.loop         = asyncio.get_event_loop()

    def connection_made(self, transport):
        self.transport = transport
        print(f"[Proxy] Bedrock proxy running on port {PROXY_PORT}")

    def datagram_received(self, data, addr):
        self.loop.create_task(self.handle(data, addr))

    async def handle(self, data, addr):
        # Ping packet — server list
        if data[0:1] == UNCONNECTED_PING:
            online = await is_online()
            if not online:
                if not self.starting:
                    self.starting = True
                    print(f"[Proxy] Bedrock — server offline, starting...")
                    await start_server()
                status = "§6Starting... Please reconnect in 30s"
            else:
                self.starting = False
                status = "§aElianaMC §f— Online!"

            pong = make_pong(data, status)
            self.transport.sendto(pong, addr)
            return

        # Game traffic — forward to MC server
        online = await is_online()
        if not online:
            await start_server()
            ready = await wait_until_online()
            if not ready: return
            await asyncio.sleep(1)

        # Forward to actual bedrock server
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(data, (MC_HOST, MC_PORT))
            sock.settimeout(1)
            try:
                resp, _ = sock.recvfrom(65535)
                self.transport.sendto(resp, addr)
            except:
                pass
            sock.close()
        except Exception as e:
            print(f"[Proxy] Bedrock forward error: {e}")

    def error_received(self, exc):
        print(f"[Proxy] Error: {exc}")

# ── Main ──────────────────────────────────────────
async def main():
    loop = asyncio.get_event_loop()
    transport, _ = await loop.create_datagram_endpoint(
        BedrockProxy,
        local_addr=(PROXY_HOST, PROXY_PORT)
    )
    print(f"[Proxy] Bedrock UDP proxy on port {PROXY_PORT}")
    try:
        await asyncio.sleep(float('inf'))
    finally:
        transport.close()

if __name__ == "__main__":
    asyncio.run(main())
