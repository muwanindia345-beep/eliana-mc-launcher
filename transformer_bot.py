import discord
from discord.ext import tasks
import os, json, math
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

TRF_PANEL = 1504049318959648852
TRF_LIVE  = 1504049124591403129
TRF_ALERT = 1504057040492822538

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree   = discord.app_commands.CommandTree(client)

trf = {
    "breaker"   : "OPEN",
    "input_v"   : 0.0,
    "output_v"  : 0.0,
    "load_kw"   : 0.0,
    "load_pct"  : 0.0,
    "current_a" : 0.0,
    "temp_c"    : 35.0,
    "status"    : "OFFLINE",
    "emergency" : False,
}

appliances = {}
msg_ids = {"live": None, "panel": None}
RATED_KW = 15.0
last_alert = ""

def load_gen():
    try:
        with open(os.path.expanduser("~/gen_state.json")) as f:
            return json.load(f)
    except: return None

def save():
    data = {**trf, "appliances": appliances, "output_v": trf["output_v"]}
    with open(os.path.expanduser("~/trf_state.json"), "w") as f:
        json.dump(data, f)

def calc():
    global last_alert
    gen = load_gen()
    gen_on = gen and gen.get("on") and gen.get("voltage_v", 0) > 50

    if not gen_on:
        trf["input_v"]  = 0.0
        trf["output_v"] = 0.0
        trf["load_kw"]  = 0.0
        trf["load_pct"] = 0.0
        trf["current_a"]= 0.0
        trf["status"]   = "NO GENERATOR INPUT"
        return

    trf["input_v"] = round(gen["voltage_v"], 1)

    if trf["emergency"] or trf["breaker"] != "CLOSED":
        trf["output_v"] = 0.0
        trf["load_kw"]  = 0.0
        trf["status"]   = "BREAKER OPEN" if not trf["emergency"] else "EMERGENCY"
        return

    # Step-down: 415V → 240V
    trf["output_v"] = 240.0

    # Load from appliances
    total_kw = sum(a.get("watt", 0) for a in appliances.values() if a.get("on")) / 1000
    trf["load_kw"]   = round(total_kw, 3)
    trf["load_pct"]  = round((total_kw / RATED_KW) * 100, 1)
    trf["current_a"] = round((total_kw * 1000) / (240 * 0.85), 2) if total_kw > 0 else 0

    # Temp
    trf["temp_c"] += ((35 + trf["load_pct"]*0.45) - trf["temp_c"]) * 0.05
    trf["temp_c"]  = round(trf["temp_c"], 1)

    # Status + alerts
    if trf["load_pct"] >= 120:
        trf["status"]  = "AUTO TRIP ☠️"
        trf["breaker"] = "TRIPPED"
        for a in appliances.values(): a["on"] = False
        last_alert = "TRIP"
    elif trf["load_pct"] >= 100:
        trf["status"] = "OVERLOAD ⚠️"
        last_alert = "OVERLOAD"
    elif trf["load_pct"] >= 80:
        trf["status"] = "WARNING 🟡"
    elif trf["temp_c"] >= 80:
        trf["status"] = "HIGH TEMP 🌡️"
        last_alert = "TEMP"
    else:
        trf["status"] = "NORMAL 🟢"
        last_alert = ""

def live_embed():
    color = (
        0xff0000 if trf["emergency"] or "TRIP" in trf["status"] else
        0xff4400 if "OVERLOAD" in trf["status"] else
        0xffcc00 if "WARNING" in trf["status"] or "TEMP" in trf["status"] else
        0x00cfff if trf["output_v"] > 0 else 0x555555
    )
    e = discord.Embed(title="🔌 CD TRANSFORMER — LIVE DATA",
        color=color, timestamp=datetime.utcnow())
    e.add_field(name="📊 STATUS",      value=f"```{trf['status']}```",     inline=False)
    e.add_field(name="⬆️ INPUT",       value=f"```{trf['input_v']} V```",  inline=True)
    e.add_field(name="⬇️ OUTPUT",      value=f"```{trf['output_v']} V```", inline=True)
    e.add_field(name="🔴 BREAKER",     value=f"```{trf['breaker']}```",    inline=True)
    e.add_field(name="⚡ LOAD",        value=f"```{trf['load_kw']} kW```", inline=True)
    e.add_field(name="📈 LOAD %",      value=f"```{trf['load_pct']}%```",  inline=True)
    e.add_field(name="🔋 CURRENT",     value=f"```{trf['current_a']} A```",inline=True)
    e.add_field(name="🌡️ TEMP",        value=f"```{trf['temp_c']} °C```",  inline=True)
    e.add_field(name="🏭 CAPACITY",    value=f"```{RATED_KW} kW```",       inline=True)
    e.add_field(name="🔌 APPLIANCES",  value=f"```{sum(1 for a in appliances.values() if a.get('on'))} active```", inline=True)
    bars = int(min(trf['load_pct'], 100) / 10)
    bar  = "█"*bars + "░"*(10-bars)
    icon = "🟢" if trf['load_pct']<80 else "🟡" if trf['load_pct']<100 else "🔴"
    e.add_field(name=f"{icon} LOAD METER",
        value=f"```{bar} {trf['load_pct']}%```", inline=False)
    e.set_footer(text="CD Step-Down Transformer | 415V → 240V | Rated 15kW")
    return e

def panel_embed():
    color = 0xff0000 if trf["emergency"] else 0x00cfff if trf["breaker"]=="CLOSED" else 0x555555
    e = discord.Embed(title="🎛️ CD TRANSFORMER — ADMIN PANEL",
        description="⚠️ Administration Only", color=color)
    e.add_field(name="BREAKER", value=f"```{trf['breaker']}```",  inline=True)
    e.add_field(name="STATUS",  value=f"```{trf['status']}```",   inline=True)
    e.add_field(name="LOAD",    value=f"```{trf['load_pct']}%```",inline=True)
    e.set_footer(text="Only admins can control transformer")
    return e

class TrfPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ CLOSE BREAKER", style=discord.ButtonStyle.success, custom_id="trf_close")
    async def close(self, interaction, button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only!", ephemeral=True); return
        if trf["emergency"]:
            await interaction.response.send_message("❌ Reset first!", ephemeral=True); return
        gen = load_gen()
        if not gen or not gen.get("on"):
            await interaction.response.send_message("❌ Generator offline!", ephemeral=True); return
        trf["breaker"] = "CLOSED"; trf["output_v"] = 240.0; trf["status"] = "NORMAL 🟢"
        await interaction.response.send_message("✅ Breaker closed! 240V ready!", ephemeral=True)

    @discord.ui.button(label="🔴 OPEN BREAKER", style=discord.ButtonStyle.danger, custom_id="trf_open")
    async def open_br(self, interaction, button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only!", ephemeral=True); return
        trf["breaker"] = "OPEN"; trf["output_v"] = 0.0
        for a in appliances.values(): a["on"] = False
        await interaction.response.send_message("🔴 Breaker opened!", ephemeral=True)

    @discord.ui.button(label="⚡ EMERGENCY", style=discord.ButtonStyle.danger, custom_id="trf_emg", row=1)
    async def emergency(self, interaction, button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only!", ephemeral=True); return
        trf["emergency"] = True; trf["breaker"] = "TRIPPED"; trf["output_v"] = 0.0
        for a in appliances.values(): a["on"] = False
        ch = client.get_channel(TRF_ALERT)
        if ch: await ch.send("🚨 **CD TRANSFORMER EMERGENCY SHUTDOWN!**")
        await interaction.response.send_message("🚨 Emergency!", ephemeral=True)

    @discord.ui.button(label="🔄 RESET", style=discord.ButtonStyle.secondary, custom_id="trf_reset", row=1)
    async def reset(self, interaction, button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only!", ephemeral=True); return
        trf["emergency"] = False; trf["breaker"] = "OPEN"
        trf["temp_c"] = 35; trf["status"] = "OFFLINE"
        await interaction.response.send_message("✅ Reset done!", ephemeral=True)

@tasks.loop(seconds=5)
async def update():
    global last_alert
    calc(); save()
    jobs = [
        ("live",  TRF_LIVE,  live_embed(),  None),
        ("panel", TRF_PANEL, panel_embed(), TrfPanel()),
    ]
    for key, ch_id, embed, view in jobs:
        ch = client.get_channel(ch_id)
        if not ch: continue
        try:
            if msg_ids[key]:
                msg = await ch.fetch_message(msg_ids[key])
                await msg.edit(embed=embed, view=view) if view else await msg.edit(embed=embed)
            else:
                msg = await ch.send(embed=embed, view=view) if view else await ch.send(embed=embed)
                msg_ids[key] = msg.id
        except Exception as ex:
            msg_ids[key] = None; print(f"Trf {key}: {ex}")

    # Alerts
    alert_ch = client.get_channel(TRF_ALERT)
    if alert_ch:
        if last_alert == "OVERLOAD":
            await alert_ch.send(f"⚠️ **TRANSFORMER OVERLOAD!** Load: {trf['load_pct']}%")
            last_alert = ""
        elif last_alert == "TEMP":
            await alert_ch.send(f"🌡️ **HIGH TEMPERATURE!** Temp: {trf['temp_c']}°C")
            last_alert = ""

@tree.command(name="trf_refresh", description="Refresh transformer channels")
async def trf_refresh(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True); return
    await interaction.response.send_message("🔄 Refreshing...", ephemeral=True)
    global msg_ids
    for ch_id in [TRF_LIVE, TRF_PANEL]:
        ch = client.get_channel(ch_id)
        if ch:
            async for m in ch.history(limit=20):
                try: await m.delete()
                except: pass
    msg_ids = {"live": None, "panel": None}
    await interaction.edit_original_response(content="✅ Refreshed!")

@client.event
async def on_ready():
    print(f"✅ Transformer Bot online!")
    await tree.sync()
    client.add_view(TrfPanel())
    update.start(); save()

client.run(BOT_TOKEN)
