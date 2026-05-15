import discord
from discord.ext import tasks
import os, json, math
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

GEN_PANEL   = 1504368500238454814
GEN_LIVE    = 1504368557289635880
GEN_WEBLINK = 1504368673152831689

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GEN_STATE_FILE  = os.path.join(BASE_DIR, "gen_state.json")
MSG_IDS_FILE    = os.path.join(BASE_DIR, "msg_ids.json")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree   = discord.app_commands.CommandTree(client)

gen = {
    "on": False, "emergency": False,
    "rpm": 0.0, "voltage_v": 0.0, "freq_hz": 0.0,
    "current_a": 0.0, "power_kw": 0.0, "power_kva": 0.0,
    "pf": 0.85, "temp_c": 25.0, "status": "OFFLINE"
}

# ── Persistent msg_ids (survives restart) ─────────────────────
def load_msg_ids():
    try:
        with open(MSG_IDS_FILE) as f:
            return json.load(f)
    except:
        return {"live": None, "panel": None, "web": None}

def save_msg_ids():
    with open(MSG_IDS_FILE, "w") as f:
        json.dump(msg_ids, f)

msg_ids = load_msg_ids()

# ── State save/load ───────────────────────────────────────────
def save():
    with open(GEN_STATE_FILE, "w") as f:
        json.dump(gen, f)

def load_state():
    try:
        with open(GEN_STATE_FILE) as f:
            data = json.load(f)
            gen.update(data)
    except:
        pass

# ── Physics calc ──────────────────────────────────────────────
def calc():
    if gen["emergency"]:
        gen["rpm"] = max(0, gen["rpm"] - 50)
        gen["status"] = "EMERGENCY STOP"
    elif not gen["on"]:
        gen["rpm"] = max(0, gen["rpm"] - 30)
        gen["status"] = "OFFLINE"
    else:
        gen["rpm"] += (3000 - gen["rpm"]) * 0.06
        gen["rpm"] = min(3000, gen["rpm"])

    rpm = gen["rpm"]
    gen["freq_hz"]   = round((rpm * 2) / 120, 2)
    gen["voltage_v"] = round((rpm / 3000) * 415, 1)

    if gen["voltage_v"] > 10:
        gen["power_kw"]  = round((rpm/3000)**1.5 * 355, 2)
        gen["power_kva"] = round(gen["power_kw"] / gen["pf"], 2)
        gen["current_a"] = round(
            gen["power_kw"]*1000 / (math.sqrt(3)*gen["voltage_v"]*gen["pf"]), 1)
    else:
        gen["power_kw"] = gen["power_kva"] = gen["current_a"] = 0.0

    if gen["on"]:
        gen["temp_c"] = min(95, gen["temp_c"] + (gen["power_kw"]/355)*0.3)
    else:
        gen["temp_c"] = max(25, gen["temp_c"] - 0.2)
    gen["temp_c"] = round(gen["temp_c"], 1)

    if not gen["emergency"]:
        if rpm >= 2900:   gen["status"] = "RUNNING FULL"
        elif rpm >= 1500: gen["status"] = "RUNNING"
        elif rpm >= 100:  gen["status"] = "STARTING UP"
        elif gen["on"]:   gen["status"] = "WARMING"
        else:             gen["status"] = "OFFLINE"

# ── Embeds ────────────────────────────────────────────────────
def live_embed():
    color = (
        0xff0000 if gen["emergency"] else
        0x00ff88 if "FULL" in gen["status"] else
        0x00cc44 if "RUNNING" in gen["status"] else
        0xffcc00 if gen["on"] else 0x555555
    )
    e = discord.Embed(title="⚡ GENERATOR — LIVE DATA", color=color, timestamp=datetime.utcnow())
    e.add_field(name="🔴 STATUS",    value=f"```{gen['status']}```",       inline=False)
    e.add_field(name="🔧 RPM",       value=f"```{gen['rpm']:.0f} / 3000```", inline=True)
    e.add_field(name="🔌 VOLTAGE",   value=f"```{gen['voltage_v']} V```",  inline=True)
    e.add_field(name="〰️ FREQUENCY", value=f"```{gen['freq_hz']} Hz```",   inline=True)
    e.add_field(name="⚡ POWER",     value=f"```{gen['power_kw']} kW```",  inline=True)
    e.add_field(name="📐 APPARENT",  value=f"```{gen['power_kva']} kVA```",inline=True)
    e.add_field(name="🔋 CURRENT",   value=f"```{gen['current_a']} A```",  inline=True)
    e.add_field(name="🌡️ TEMP",      value=f"```{gen['temp_c']} °C```",    inline=True)
    e.add_field(name="📊 PF",        value=f"```{gen['pf']}```",           inline=True)
    e.set_footer(text="3-Phase AC | 2-Pole | Rated 355kW 415V 50Hz")
    return e

def panel_embed():
    color = 0xff0000 if gen["emergency"] else 0x00cc44 if gen["on"] else 0x555555
    e = discord.Embed(title="🎛️ GENERATOR — ADMIN PANEL",
        description="⚠️ Administration Only", color=color)
    status = "🚨 EMERGENCY" if gen["emergency"] else "🟢 ONLINE" if gen["on"] else "🔴 OFFLINE"
    e.add_field(name="STATUS",   value=f"```{status}```",          inline=False)
    e.add_field(name="⚡ POWER", value=f"`{gen['power_kw']} kW`",  inline=True)
    e.add_field(name="🔧 RPM",   value=f"`{gen['rpm']:.0f}`",      inline=True)
    e.add_field(name="🔌 VOLT",  value=f"`{gen['voltage_v']} V`",  inline=True)
    e.set_footer(text="Only admins can control generator")
    return e

def web_embed():
    e = discord.Embed(title="🌐 GENERATOR — 3D WEB MODEL",
        description="Live 3D Visualization", color=0x00cfff)
    e.add_field(name="🔗 URL",
        value="`https://power-grid-empire.onrender.com/generator31.html`", inline=False)
    e.add_field(name="📊 Features",
        value="• Real-time RPM & Voltage\n• 3D rotating armature\n• Live waveform\n• Sound effects",
        inline=False)
    return e

# ── Panel View ────────────────────────────────────────────────
class GenPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def check_admin(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="▶️ START", style=discord.ButtonStyle.success, custom_id="gen_start")
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not await self.check_admin(interaction): return
            if gen["emergency"]:
                await interaction.response.send_message("❌ Reset first!", ephemeral=True); return
            gen["on"] = True
            save()
            await interaction.response.send_message("✅ Generator starting...", ephemeral=True)
        except Exception as e:
            print(f"START error: {e}")
            try: await interaction.response.send_message("❌ Error occurred!", ephemeral=True)
            except: pass

    @discord.ui.button(label="⏹️ STOP", style=discord.ButtonStyle.danger, custom_id="gen_stop")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not await self.check_admin(interaction): return
            gen["on"] = False
            save()
            await interaction.response.send_message("🔴 Generator stopping...", ephemeral=True)
        except Exception as e:
            print(f"STOP error: {e}")
            try: await interaction.response.send_message("❌ Error occurred!", ephemeral=True)
            except: pass

    @discord.ui.button(label="⚡ EMERGENCY", style=discord.ButtonStyle.danger, custom_id="gen_emg", row=1)
    async def emergency(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not await self.check_admin(interaction): return
            gen["on"] = False; gen["emergency"] = True; gen["status"] = "EMERGENCY STOP"
            save()
            await interaction.response.send_message("🚨 Emergency stop activated!", ephemeral=True)
        except Exception as e:
            print(f"EMERGENCY error: {e}")
            try: await interaction.response.send_message("❌ Error occurred!", ephemeral=True)
            except: pass

    @discord.ui.button(label="🔄 RESET", style=discord.ButtonStyle.secondary, custom_id="gen_reset", row=1)
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not await self.check_admin(interaction): return
            gen["emergency"] = False; gen["rpm"] = 0
            gen["temp_c"] = 25; gen["status"] = "OFFLINE"
            save()
            await interaction.response.send_message("✅ Reset done!", ephemeral=True)
        except Exception as e:
            print(f"RESET error: {e}")
            try: await interaction.response.send_message("❌ Error occurred!", ephemeral=True)
            except: pass

# ── Update loop ───────────────────────────────────────────────
@tasks.loop(seconds=5)
async def update():
    calc(); save()
    jobs = [
        ("live",  GEN_LIVE,    live_embed(),  None),
        ("panel", GEN_PANEL,   panel_embed(), GenPanel()),
        ("web",   GEN_WEBLINK, web_embed(),   None),
    ]
    changed = False
    for key, ch_id, embed, view in jobs:
        ch = client.get_channel(ch_id)
        if not ch: continue
        try:
            if msg_ids[key]:
                msg = await ch.fetch_message(msg_ids[key])
                if view:
                    await msg.edit(embed=embed, view=view)
                else:
                    await msg.edit(embed=embed)
            else:
                msg = await ch.send(embed=embed, view=view) if view else await ch.send(embed=embed)
                msg_ids[key] = msg.id
                changed = True
        except discord.NotFound:
            msg_ids[key] = None
            changed = True
            print(f"Gen {key}: message not found, will recreate")
        except Exception as ex:
            print(f"Gen {key}: {ex}")
    if changed:
        save_msg_ids()

@tree.command(name="gen_refresh", description="Refresh generator channels")
async def gen_refresh(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True); return
    await interaction.response.send_message("🔄 Refreshing...", ephemeral=True)
    for ch_id in [GEN_LIVE, GEN_PANEL, GEN_WEBLINK]:
        ch = client.get_channel(ch_id)
        if ch:
            async for m in ch.history(limit=20):
                try: await m.delete()
                except: pass
    msg_ids.update({"live": None, "panel": None, "web": None})
    save_msg_ids()
    await interaction.edit_original_response(content="✅ Refreshed!")

@client.event
async def on_ready():
    print(f"✅ Generator Bot online!")
    load_state()
    client.add_view(GenPanel())  # persistent view register
    await tree.sync()
    update.start()
    print(f"📂 State loaded | msg_ids: {msg_ids}")

client.run(BOT_TOKEN)
