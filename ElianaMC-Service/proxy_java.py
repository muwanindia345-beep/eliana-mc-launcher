import asyncio
import json
import httpx
import time
import struct

PROXY_HOST    = "0.0.0.0"
PROXY_PORT    = 25565
MC_HOST       = "127.0.0.1"
MC_PORT       = 25566
BACKEND       = "http://localhost:8007"

# ── Varint helpers ────────────────────────────────
def pack_varint(val):
    out = b""
    while True:
        b = val & 0x7F
        val >>= 7
        out += bytes([b | (0x80 if val else 0)])
        if not val: break
    return out

async def read_varint(reader):
    result = shift = 0
    while True:
        b = await reader.read(1)
        if not b: return 0
        val = b[0]
        result |= (val & 0x7F) << shift
        if not (val & 0x80): break
        shift += 7
    return result

# ── Packet helpers ────────────────────────────────
def make_packet(packet_id, data=b""):
    inner = pack_varint(packet_id) + data
    return pack_varint(len(inner)) + inner

def pack_string(s):
    encoded = s.encode("utf-8")
    return pack_varint(len(encoded)) + encoded

# ── Status response ───────────────────────────────
def make_status(description, version_name="Starting...", protocol=47):
    data = {
        "version": {"name": version_name, "protocol": protocol},
        "players": {"max": 20, "online": 0, "sample": []},
        "description": {"text": description}
    }
    payload = json.dumps(data).encode("utf-8")
    inner   = pack_varint(0x00) + pack_varint(len(payload)) + payload
    return pack_varint(len(inner)) + inner

# ── Disconnect packet ─────────────────────────────
def make_disconnect(message):
    msg  = json.dumps({"text": message, "color": "yellow"})
    data = pack_string(msg)
    return make_packet(0x00, data)

# ── Login success (fake) ──────────────────────────
def make_login_success(username):
    uuid = "00000000-0000-0000-0000-000000000000"
    data = pack_string(uuid) + pack_string(username)
    return make_packet(0x02, data)

# ── Join game (fake waiting room) ─────────────────
def make_join_game():
    data  = struct.pack(">i", 1)          # entity id
    data += struct.pack(">B", 0)          # gamemode survival
    data += struct.pack(">b", 0)          # dimension overworld
    data += struct.pack(">B", 0)          # difficulty peaceful
    data += struct.pack(">B", 20)         # max players
    data += pack_string("flat")           # level type
    data += struct.pack(">?", False)      # reduced debug
    return make_packet(0x23, data)

# ── Chat message ──────────────────────────────────
def make_chat(message, color="yellow"):
    msg  = json.dumps({"text": message, "color": color})
    data = pack_string(msg) + struct.pack(">B", 0)
    return make_packet(0x02, data)

# ── Title packet ──────────────────────────────────
def make_title(title, subtitle="", fade_in=10, stay=70, fade_out=20):
    def title_pkt(action, text):
        msg  = json.dumps({"text": text})
        data = pack_varint(action) + pack_string(msg)
        return make_packet(0x45, data)

    pkts  = title_pkt(0, title)
    pkts += title_pkt(1, subtitle)
    # Times
    times = pack_varint(2) + struct.pack(">iii", fade_in, stay, fade_out)
    pkts += make_packet(0x45, times)
    return pkts

# ── Backend helpers ───────────────────────────────
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

async def wait_online(timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        if await is_online():
            return True
        await asyncio.sleep(3)
    return False

# ── Forward traffic ───────────────────────────────
async def forward(reader, writer):
    try:
        while True:
            data = await reader.read(4096)
            if not data: break
            writer.write(data)
            await writer.drain()
    except:
        pass

# ── Handle connection ─────────────────────────────
async def handle(reader, writer):
    addr = writer.get_extra_info("peername")
    print(f"[Java Proxy] Connection: {addr}")

    try:
        # Read handshake
        pkt_len  = await read_varint(reader)
        pkt_data = await reader.read(pkt_len)
        if not pkt_data: writer.close(); return

        next_state = pkt_data[-1]

        # ── Status ping ───────────────────────────
        if next_state == 1:
            online = await is_online()
            if not online:
                await start_server()
                motd = "§6⚡ Server is Starting...\n§ePlease wait and join again!"
            else:
                motd = "§aElianaMC §f— §2Online!"

            await reader.read(2)  # status request
            writer.write(make_status(motd))
            await writer.drain()

            try:
                ping = await asyncio.wait_for(reader.read(10), timeout=3)
                writer.write(ping)
                await writer.drain()
            except: pass
            writer.close(); return

        # ── Login ─────────────────────────────────
        if next_state == 2:
            # Read login start
            login_len  = await read_varint(reader)
            login_data = await reader.read(login_len)

            # Extract username
            username = "Player"
            try:
                offset   = 1  # skip packet id
                str_len  = login_data[offset]
                username = login_data[offset+1:offset+1+str_len].decode("utf-8")
            except: pass

            print(f"[Java Proxy] Player: {username}")

            online = await is_online()

            if not online:
                print(f"[Java Proxy] Starting server for {username}...")
                await start_server()

                # Send login success + join game (waiting room)
                writer.write(make_login_success(username))
                await writer.drain()
                writer.write(make_join_game())
                await writer.drain()

                # Send waiting messages
                messages = [
                    ("§6⚡ Server is starting, please wait...", "gold"),
                    ("§eThis may take 2-5 minutes on this server.", "yellow"),
                    ("§aYou will be transferred automatically!", "green"),
                ]
                for msg, color in messages:
                    writer.write(make_chat(msg, color))
                    await writer.drain()
                    await asyncio.sleep(0.5)

                # Wait loop — send updates
                start_time = time.time()
                elapsed    = 0
                ready      = False

                while elapsed < 300:
                    await asyncio.sleep(10)
                    elapsed = int(time.time() - start_time)

                    if await is_online():
                        ready = True
                        break

                    mins = elapsed // 60
                    secs = elapsed % 60
                    writer.write(make_chat(
                        f"§7Still starting... §e{mins}m {secs}s elapsed", "gray"
                    ))
                    await writer.drain()

                if not ready:
                    writer.write(make_disconnect("§cServer failed to start. Try again later."))
                    await writer.drain()
                    writer.close(); return

                # Server ready!
                writer.write(make_chat("§a✅ Server is online! Transferring...", "green"))
                await writer.drain()
                await asyncio.sleep(2)

                # Disconnect — player reconnects automatically
                writer.write(make_disconnect(
                    "§aServer is ready!\n§ePlease reconnect now."
                ))
                await writer.drain()
                writer.close(); return

            else:
                # Server already online — forward directly
                try:
                    mc_r, mc_w = await asyncio.wait_for(
                        asyncio.open_connection(MC_HOST, MC_PORT),
                        timeout=10
                    )
                    # Replay handshake + login
                    mc_w.write(pack_varint(len(pkt_data)) + pkt_data)
                    mc_w.write(pack_varint(len(login_data)) + login_data)
                    await mc_w.drain()

                    await asyncio.gather(
                        forward(reader, mc_w),
                        forward(mc_r, writer)
                    )
                except Exception as e:
                    print(f"[Java Proxy] Forward error: {e}")
                    writer.close()

    except Exception as e:
        print(f"[Java Proxy] Error: {e}")
        try: writer.close()
        except: pass

# ── Main ──────────────────────────────────────────
async def main():
    server = await asyncio.start_server(handle, PROXY_HOST, PROXY_PORT)
    print(f"[Java Proxy] Running on port {PROXY_PORT} → MC port {MC_PORT}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
