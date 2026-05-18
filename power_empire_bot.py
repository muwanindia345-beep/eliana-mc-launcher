import os, json, math, datetime, random, requests, asyncio, re
from pathlib import Path
from discord.ext import commands, tasks
import discord

# ══════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
NASA_KEY  = os.getenv("NASA_API_KEY", "DEMO_KEY")
JWST_KEY  = os.getenv("JWST_API_KEY", "")

# Generator channels
GEN_PANEL   = int(os.getenv("GEN_PANEL",   "1504368500238454814"))
GEN_LIVE    = int(os.getenv("GEN_LIVE",    "1504368557289635880"))
GEN_WEBLINK = int(os.getenv("GEN_WEBLINK", "1504368673152831689"))

# Transformer channels
TRF_PANEL = int(os.getenv("TRF_PANEL", "1504049318959648852"))
TRF_LIVE  = int(os.getenv("TRF_LIVE",  "1504049124591403129"))
TRF_ALERT = int(os.getenv("TRF_ALERT", "1504057040492822538"))

# Satellite/JWST channels
APOD_CH = int(os.getenv("APOD_CHANNEL_ID",  "0"))
DATA_CH = int(os.getenv("DATA_CHANNEL_ID",  "0"))
ALERT_CH_SAT = int(os.getenv("ALERT_CHANNEL_ID", "0"))
JWST_CH = int(os.getenv("JWST_CHANNEL_ID",  "0"))

# ══════════════════════════════════════════════════
#  BOT SETUP
# ══════════════════════════════════════════════════
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ══════════════════════════════════════════════════
#  GENERATOR STATE
# ══════════════════════════════════════════════════
gen = {
    "on": False, "emergency": False,
    "rpm": 0.0, "voltage_v": 0.0, "freq_hz": 0.0,
    "current_a": 0.0, "power_kw": 0.0, "power_kva": 0.0,
    "pf": 0.85, "temp_c": 25.0, "status": "OFFLINE"
}
gen_msg = {"live": None, "panel": None, "web": None}

def save_gen():
    with open("gen_state.json", "w") as f:
        json.dump(gen, f)

def calc_gen():
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
        gen["current_a"] = round(gen["power_kw"]*1000 / (math.sqrt(3)*gen["voltage_v"]*gen["pf"]), 1)
    else:
        gen["power_kw"] = gen["power_kva"] = gen["current_a"] = 0.0

    if gen["on"]:
        gen["temp_c"] = min(95, gen["temp_c"] + (gen["power_kw"]/355)*0.3)
    else:
        gen["temp_c"] = max(25, gen["temp_c"] - 0.2)
    gen["temp_c"] = round(gen["temp_c"], 1)

    if not gen["emergency"]:
        rpm = gen["rpm"]
        if rpm >= 2900:   gen["status"] = "RUNNING FULL"
        elif rpm >= 1500: gen["status"] = "RUNNING"
        elif rpm >= 100:  gen["status"] = "STARTING UP"
        elif gen["on"]:   gen["status"] = "WARMING"
        else:             gen["status"] = "OFFLINE"

def gen_live_embed():
    color = (0xff0000 if gen["emergency"] else
             0x00ff88 if "FULL" in gen["status"] else
             0x00cc44 if "RUNNING" in gen["status"] else
             0xffcc00 if gen["on"] else 0x555555)
    e = discord.Embed(title="⚡ GENERATOR — LIVE DATA", color=color,
                      timestamp=datetime.datetime.now(datetime.UTC))
    e.add_field(name="🔴 STATUS",    value=f"```{gen['status']}```",           inline=False)
    e.add_field(name="🔧 RPM",       value=f"```{gen['rpm']:.0f} / 3000```",   inline=True)
    e.add_field(name="🔌 VOLTAGE",   value=f"```{gen['voltage_v']} V```",      inline=True)
    e.add_field(name="〰️ FREQUENCY", value=f"```{gen['freq_hz']} Hz```",       inline=True)
    e.add_field(name="⚡ POWER",     value=f"```{gen['power_kw']} kW```",       inline=True)
    e.add_field(name="📐 APPARENT",  value=f"```{gen['power_kva']} kVA```",    inline=True)
    e.add_field(name="🔋 CURRENT",   value=f"```{gen['current_a']} A```",      inline=True)
    e.add_field(name="🌡️ TEMP",      value=f"```{gen['temp_c']} °C```",        inline=True)
    e.add_field(name="📊 PF",        value=f"```{gen['pf']}```",               inline=True)
    e.set_footer(text="3-Phase AC | 2-Pole | Rated 355kW 415V 50Hz")
    return e

def gen_panel_embed():
    color = 0xff0000 if gen["emergency"] else 0x00cc44 if gen["on"] else 0x555555
    e = discord.Embed(title="🎛️ GENERATOR — ADMIN PANEL",
                      description="⚠️ Administration Only", color=color)
    status = "🚨 EMERGENCY" if gen["emergency"] else "🟢 ONLINE" if gen["on"] else "🔴 OFFLINE"
    e.add_field(name="STATUS",  value=f"```{status}```",          inline=False)
    e.add_field(name="⚡ POWER", value=f"`{gen['power_kw']} kW`", inline=True)
    e.add_field(name="🔧 RPM",  value=f"`{gen['rpm']:.0f}`",      inline=True)
    e.add_field(name="🔌 VOLT", value=f"`{gen['voltage_v']} V`",  inline=True)
    e.set_footer(text="Only admins can control generator")
    return e

def gen_web_embed():
    e = discord.Embed(title="🌐 GENERATOR — 3D WEB MODEL",
                      description="Live 3D Visualization", color=0x00cfff)
    e.add_field(name="🔗 URL",
                value="`https://powe-grid-empire.onrender.com/generator31.html`", inline=False)
    return e

class GenPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="▶️ START", style=discord.ButtonStyle.success, custom_id="gen_start")
    async def start(self, interaction, button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only!", ephemeral=True); return
        if gen["emergency"]:
            await interaction.response.send_message("❌ Reset first!", ephemeral=True); return
        gen["on"] = True
        await interaction.response.send_message("✅ Generator starting...", ephemeral=True)

    @discord.ui.button(label="⏹️ STOP", style=discord.ButtonStyle.danger, custom_id="gen_stop")
    async def stop(self, interaction, button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only!", ephemeral=True); return
        gen["on"] = False
        await interaction.response.send_message("🔴 Stopping...", ephemeral=True)

    @discord.ui.button(label="⚡ EMERGENCY", style=discord.ButtonStyle.danger, custom_id="gen_emg", row=1)
    async def emergency(self, interaction, button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only!", ephemeral=True); return
        gen["on"] = False; gen["emergency"] = True; gen["status"] = "EMERGENCY STOP"
        await interaction.response.send_message("🚨 Emergency stop!", ephemeral=True)

    @discord.ui.button(label="🔄 RESET", style=discord.ButtonStyle.secondary, custom_id="gen_reset", row=1)
    async def reset(self, interaction, button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only!", ephemeral=True); return
        gen["emergency"] = False; gen["rpm"] = 0; gen["temp_c"] = 25; gen["status"] = "OFFLINE"
        await interaction.response.send_message("✅ Reset!", ephemeral=True)

# ══════════════════════════════════════════════════
#  TRANSFORMER STATE
# ══════════════════════════════════════════════════
trf = {
    "breaker": "OPEN", "input_v": 0.0, "output_v": 0.0,
    "load_kw": 0.0, "load_pct": 0.0, "current_a": 0.0,
    "temp_c": 35.0, "status": "OFFLINE", "emergency": False,
}
appliances = {}
trf_msg = {"live": None, "panel": None}
last_alert = ""

def save_trf():
    with open("trf_state.json", "w") as f:
        json.dump({**trf, "appliances": appliances}, f)

def calc_trf():
    global last_alert
    if trf["emergency"] or trf["breaker"] != "CLOSED":
        trf["output_v"] = 0.0; trf["load_kw"] = 0.0
        trf["status"] = "EMERGENCY" if trf["emergency"] else "BREAKER OPEN"
        if gen["voltage_v"] < 50:
            trf["input_v"] = 0.0; trf["status"] = "NO GENERATOR INPUT"
        return

    if gen["voltage_v"] < 50:
        trf["input_v"] = 0.0; trf["output_v"] = 0.0
        trf["load_kw"] = 0.0; trf["load_pct"] = 0.0
        trf["status"] = "NO GENERATOR INPUT"
        return

    trf["input_v"]  = round(gen["voltage_v"], 1)
    trf["output_v"] = 240.0
    total_kw = sum(a.get("watt", 0) for a in appliances.values() if a.get("on")) / 1000
    trf["load_kw"]   = round(total_kw, 3)
    trf["load_pct"]  = round((total_kw / RATED_KW) * 100, 1)
    trf["current_a"] = round((total_kw * 1000) / (240 * 0.85), 2) if total_kw > 0 else 0
    trf["temp_c"] += ((35 + trf["load_pct"]*0.45) - trf["temp_c"]) * 0.05
    trf["temp_c"]  = round(trf["temp_c"], 1)

    if trf["load_pct"] >= 120:
        trf["status"] = "AUTO TRIP ☠️"; trf["breaker"] = "TRIPPED"
        for a in appliances.values(): a["on"] = False; last_alert = "TRIP"
    elif trf["load_pct"] >= 100: trf["status"] = "OVERLOAD ⚠️"; last_alert = "OVERLOAD"
    elif trf["load_pct"] >= 80:  trf["status"] = "WARNING 🟡"
    elif trf["temp_c"] >= 80:    trf["status"] = "HIGH TEMP 🌡️"; last_alert = "TEMP"
    else:                         trf["status"] = "NORMAL 🟢"; last_alert = ""

def trf_live_embed():
    color = (0xff0000 if trf["emergency"] or "TRIP" in trf["status"] else
             0xff4400 if "OVERLOAD" in trf["status"] else
             0xffcc00 if "WARNING" in trf["status"] or "TEMP" in trf["status"] else
             0x00cfff if trf["output_v"] > 0 else 0x555555)
    e = discord.Embed(title="🔌 CD TRANSFORMER — LIVE DATA", color=color,
                      timestamp=datetime.datetime.now(datetime.UTC))
    e.add_field(name="📊 STATUS",    value=f"```{trf['status']}```",     inline=False)
    e.add_field(name="⬆️ INPUT",     value=f"```{trf['input_v']} V```",  inline=True)
    e.add_field(name="⬇️ OUTPUT",    value=f"```{trf['output_v']} V```", inline=True)
    e.add_field(name="🔴 BREAKER",   value=f"```{trf['breaker']}```",    inline=True)
    e.add_field(name="⚡ LOAD",      value=f"```{trf['load_kw']} kW```", inline=True)
    e.add_field(name="📈 LOAD %",    value=f"```{trf['load_pct']}%```",  inline=True)
    e.add_field(name="🔋 CURRENT",   value=f"```{trf['current_a']} A```",inline=True)
    e.add_field(name="🌡️ TEMP",      value=f"```{trf['temp_c']} °C```",  inline=True)
    bars = int(min(trf['load_pct'], 100) / 10)
    bar  = "█"*bars + "░"*(10-bars)
    icon = "🟢" if trf['load_pct']<80 else "🟡" if trf['load_pct']<100 else "🔴"
    e.add_field(name=f"{icon} LOAD METER",
                value=f"```{bar} {trf['load_pct']}%```", inline=False)
    e.set_footer(text="CD Step-Down | 415V → 240V | Rated 15kW")
    return e

def trf_panel_embed():
    color = 0xff0000 if trf["emergency"] else 0x00cfff if trf["breaker"]=="CLOSED" else 0x555555
    e = discord.Embed(title="🎛️ CD TRANSFORMER — ADMIN PANEL",
                      description="⚠️ Administration Only", color=color)
    e.add_field(name="BREAKER", value=f"```{trf['breaker']}```",   inline=True)
    e.add_field(name="STATUS",  value=f"```{trf['status']}```",    inline=True)
    e.add_field(name="LOAD",    value=f"```{trf['load_pct']}%```", inline=True)
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
        if gen["voltage_v"] < 50:
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
        ch = bot.get_channel(TRF_ALERT)
        if ch: await ch.send("🚨 **CD TRANSFORMER EMERGENCY SHUTDOWN!**")
        await interaction.response.send_message("🚨 Emergency!", ephemeral=True)

    @discord.ui.button(label="🔄 RESET", style=discord.ButtonStyle.secondary, custom_id="trf_reset", row=1)
    async def reset(self, interaction, button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only!", ephemeral=True); return
        trf["emergency"] = False; trf["breaker"] = "OPEN"
        trf["temp_c"] = 35; trf["status"] = "OFFLINE"
        await interaction.response.send_message("✅ Reset!", ephemeral=True)

# ══════════════════════════════════════════════════
#  SATELLITE
# ══════════════════════════════════════════════════
class Satellite:
    def __init__(self):
        self.alt=549.99; self.batt=98.0; self.solar=0.0
        self.hot=82.0; self.cold=-42.0; self.orbit=1
        self.pkts=0; self.uptime=0; self.cpu=28.5; self.signal=92.0

    def tick(self, s=300):
        self.uptime+=s; self.alt=round(max(540,min(560,self.alt+random.uniform(-.03,.02))),2)
        h=datetime.datetime.now(datetime.UTC).hour; sun=6<=h<=18
        self.solar=round(random.uniform(1380,1460),1) if sun else 0.0
        self.batt=round(min(100,self.batt+random.uniform(.1,.6)),1) if sun else round(max(55,self.batt-random.uniform(.1,.4)),1)
        self.hot=round(random.uniform(75,90),1); self.cold=round(random.uniform(-55,-40),1)
        self.cpu=round(random.uniform(25,38),1); self.signal=round(random.uniform(85,98),1)
        self.orbit=(self.uptime//5400)+1; self.pkts+=random.randint(120,200)

    def uptime_str(self):
        s=self.uptime; d,s=divmod(s,86400); h,s=divmod(s,3600); m,s=divmod(s,60)
        return f"{d}d {h:02d}h {m:02d}m {s:02d}s"

    def status(self):
        if self.batt>80: return "🟢","NOMINAL"
        if self.batt>50: return "🟡","CAUTION"
        return "🔴","CRITICAL"

sat = Satellite()

PLANETS = {
    "Mercury":{"id":"199","emoji":"☿"},"Venus":{"id":"299","emoji":"♀"},
    "Earth":{"id":"399","emoji":"🌍"},"Mars":{"id":"499","emoji":"♂"},
    "Jupiter":{"id":"599","emoji":"♃"},"Saturn":{"id":"699","emoji":"♄"},
    "Uranus":{"id":"799","emoji":"⛢"},"Neptune":{"id":"899","emoji":"♆"},
}

def nasa_api(ep, params=None):
    p=(params or {}); p["api_key"]=NASA_KEY
    try:
        r=requests.get(f"https://api.nasa.gov{ep}",params=p,timeout=15)
        return r.json()
    except: return None

def get_iss():
    try:
        r=requests.get("http://api.open-notify.org/iss-now.json",timeout=10)
        d=r.json()["iss_position"]
        return float(d["latitude"]),float(d["longitude"])
    except: return None,None

def get_crew():
    try:
        r=requests.get("http://api.open-notify.org/astros.json",timeout=10)
        return r.json()
    except: return None

def get_epic():
    try:
        r=requests.get("https://epic.gsfc.nasa.gov/api/natural",timeout=12)
        d=r.json()
        if d:
            l=d[0]; date=l["date"][:10].replace("-","/")
            return f"https://epic.gsfc.nasa.gov/archive/natural/{date}/png/{l['image']}.png",l["date"][:10]
    except: pass
    return None,None

def get_planet_dist(pid):
    try:
        today=datetime.date.today().isoformat()
        tomorrow=(datetime.date.today()+datetime.timedelta(days=1)).isoformat()
        r=requests.get("https://ssd.jpl.nasa.gov/api/horizons.api",params={
            "format":"json","COMMAND":f"'{pid}'","OBJ_DATA":"'NO'",
            "MAKE_EPHEM":"'YES'","EPHEM_TYPE":"'VECTORS'","CENTER":"'500@10'",
            "START_TIME":f"'{today}'","STOP_TIME":f"'{tomorrow}'",
            "STEP_SIZE":"'1 d'","OUT_UNITS":"'AU-D'"
        },timeout=20)
        txt=r.json().get("result","")
        m=re.search(r'X\s*=\s*([-\d.E+]+)\s+Y\s*=\s*([-\d.E+]+)\s+Z\s*=\s*([-\d.E+]+)',txt)
        if m:
            x,y,z=float(m.group(1)),float(m.group(2)),float(m.group(3))
            au=round((x**2+y**2+z**2)**0.5,4); km=round(au*149597870.7,0)
            return au,km
    except: pass
    return None,None

def E_telemetry():
    em,st=sat.status(); lat,lon=get_iss()
    e=discord.Embed(title=f"{em} SATELLITE-01 · Live Telemetry",colour=0x00e5ff,
                    timestamp=datetime.datetime.now(datetime.UTC))
    e.add_field(name="🛰️ Altitude",  value=f"`{sat.alt} km`",     inline=True)
    e.add_field(name="🔋 Battery",   value=f"`{sat.batt}%`",       inline=True)
    e.add_field(name="☀️ Solar",     value=f"`{sat.solar} W`",     inline=True)
    e.add_field(name="🌡️ Hot Side",  value=f"`+{sat.hot}°C`",     inline=True)
    e.add_field(name="❄️ Cold Side", value=f"`{sat.cold}°C`",     inline=True)
    e.add_field(name="💻 CPU",       value=f"`{sat.cpu}°C`",       inline=True)
    e.add_field(name="📡 Signal",    value=f"`{sat.signal}%`",     inline=True)
    e.add_field(name="🔄 Orbit",     value=f"`{sat.orbit}`",       inline=True)
    e.add_field(name="📦 Packets",   value=f"`{sat.pkts:,}`",      inline=True)
    e.add_field(name="⏱️ Uptime",    value=f"`{sat.uptime_str()}`",inline=True)
    e.add_field(name="✅ Status",    value=f"`{st}`",               inline=True)
    if lat: e.add_field(name="🚀 ISS",value=f"`Lat {lat:+.3f}° Lon {lon:+.3f}°`",inline=False)
    e.set_author(name="🛰️ SATELLITE-01 · Ground Station · LEO 550km")
    e.set_footer(text=f"🕐 {datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    return e

# ══════════════════════════════════════════════════
#  JWST
# ══════════════════════════════════════════════════
STATE_FILE = Path("jwst_state.json")

def load_jwst():
    try:
        if STATE_FILE.exists(): return json.loads(STATE_FILE.read_text())
    except: pass
    return {"last_id": None, "last_date": None}

def save_jwst(s): STATE_FILE.write_text(json.dumps(s, indent=2))

jwst_state = load_jwst()

def get_jwst():
    try:
        r=requests.get("https://api.jwstapi.com/all/type/jpg",
                       headers={"X-Api-Key": JWST_KEY}, timeout=15)
        d=r.json()
        if d:
            img=d[0]
            return {"id":img.get("id",""),"title":img.get("details",{}).get("mission","JWST"),
                    "url":img.get("file_url",""),"desc":img.get("details",{}).get("description",""),
                    "date":img.get("details",{}).get("date","")}
    except: pass
    return None

# ══════════════════════════════════════════════════
#  TASKS
# ══════════════════════════════════════════════════
async def find_or_update(ch_id, embed, view=None, msg_dict=None, key=None):
    ch = bot.get_channel(ch_id)
    if not ch: return
    try:
        if msg_dict and msg_dict.get(key):
            msg = await ch.fetch_message(msg_dict[key])
            await msg.edit(embed=embed, view=view) if view else await msg.edit(embed=embed)
            return
        async for msg in ch.history(limit=15):
            if msg.author == bot.user:
                await msg.edit(embed=embed, view=view) if view else await msg.edit(embed=embed)
                if msg_dict is not None and key: msg_dict[key] = msg.id
                return
        msg = await ch.send(embed=embed, view=view) if view else await ch.send(embed=embed)
        if msg_dict is not None and key: msg_dict[key] = msg.id
    except discord.NotFound:
        if msg_dict and key: msg_dict[key] = None
    except Exception as ex:
        print(f"Update error: {ex}")

@tasks.loop(seconds=5)
async def gen_task():
    calc_gen(); save_gen()
    await find_or_update(GEN_LIVE,    gen_live_embed(),  None,      gen_msg, "live")
    await find_or_update(GEN_PANEL,   gen_panel_embed(), GenPanel(),gen_msg, "panel")
    await find_or_update(GEN_WEBLINK, gen_web_embed(),   None,      gen_msg, "web")

@tasks.loop(seconds=5)
async def trf_task():
    global last_alert
    calc_trf(); save_trf()
    await find_or_update(TRF_LIVE,  trf_live_embed(),  None,       trf_msg, "live")
    await find_or_update(TRF_PANEL, trf_panel_embed(), TrfPanel(), trf_msg, "panel")
    if last_alert:
        ch = bot.get_channel(TRF_ALERT)
        if ch:
            if last_alert == "OVERLOAD":
                await ch.send(f"⚠️ **TRANSFORMER OVERLOAD!** Load: {trf['load_pct']}%")
            elif last_alert == "TEMP":
                await ch.send(f"🌡️ **HIGH TEMPERATURE!** Temp: {trf['temp_c']}°C")
            last_alert = ""

@tasks.loop(minutes=5)
async def sat_task():
    ch = bot.get_channel(DATA_CH)
    if not ch: return
    sat.tick(300)
    await ch.send(embed=E_telemetry())

@tasks.loop(hours=1)
async def apod_task():
    ch = bot.get_channel(APOD_CH)
    if not ch: return
    d = nasa_api("/planetary/apod")
    if d and "title" in d:
        e = discord.Embed(title=f"🌌 {d.get('title','')}",
                          description=(d.get("explanation","")[:900]+"…"),colour=0x1a1040,
                          timestamp=datetime.datetime.now(datetime.UTC))
        if d.get("media_type")=="image": e.set_image(url=d.get("hdurl") or d.get("url",""))
        e.set_footer(text=f"📅 {d.get('date','')} · © {d.get('copyright','NASA')}")
        await ch.send(embed=e)

@tasks.loop(hours=24)
async def jwst_task():
    ch = bot.get_channel(JWST_CH)
    if not ch: return
    today = datetime.date.today().isoformat()
    if jwst_state.get("last_date") == today: return
    img = get_jwst()
    if img and img["id"] != jwst_state.get("last_id"):
        e = discord.Embed(title=f"🔭 {img['title']}",
                          description=img['desc'][:500]+"…",colour=0x4b0082,
                          timestamp=datetime.datetime.now(datetime.UTC))
        e.set_image(url=img['url'])
        e.set_author(name="🔭 James Webb Space Telescope")
        e.set_footer(text=f"📅 {img['date']}")
        await ch.send(embed=e)
        jwst_state["last_id"] = img["id"]; jwst_state["last_date"] = today
        save_jwst(jwst_state)

# ══════════════════════════════════════════════════
#  PREFIX COMMANDS
# ══════════════════════════════════════════════════
@bot.command(name="status")
async def cmd_status(ctx):
    sat.tick(60); await ctx.send(embed=E_telemetry())

@bot.command(name="iss")
async def cmd_iss(ctx):
    lat,lon=get_iss(); crew=get_crew()
    if lat:
        e=discord.Embed(title="🚀 ISS Live Position",colour=0x00e5ff,
                        timestamp=datetime.datetime.now(datetime.UTC))
        e.add_field(name="📍 Lat",value=f"`{lat:+.4f}°`",inline=True)
        e.add_field(name="📍 Lon",value=f"`{lon:+.4f}°`",inline=True)
        e.add_field(name="🗺️ Map",value=f"[View](https://www.google.com/maps?q={lat},{lon}&z=4)",inline=True)
        if crew:
            e.add_field(name=f"👨‍🚀 Crew ({crew.get('number',0)})",
                        value="\n".join(f"• {p['name']} ({p['craft']})" for p in crew.get("people",[])),inline=False)
        await ctx.send(embed=e)
    else: await ctx.send("❌ ISS tracker offline.")

@bot.command(name="apod")
async def cmd_apod(ctx):
    async with ctx.typing():
        d=nasa_api("/planetary/apod")
        if d and "title" in d:
            e=discord.Embed(title=f"🌌 {d.get('title','')}",
                            description=(d.get("explanation","")[:900]+"…"),colour=0x1a1040,
                            timestamp=datetime.datetime.now(datetime.UTC))
            if d.get("media_type")=="image": e.set_image(url=d.get("hdurl") or d.get("url",""))
            await ctx.send(embed=e)
        else: await ctx.send("❌ APOD unavailable.")

@bot.command(name="webb")
async def cmd_webb(ctx):
    img=get_jwst()
    if img:
        e=discord.Embed(title=f"🔭 {img['title']}",description=img['desc'][:500]+"…",
                        colour=0x4b0082,timestamp=datetime.datetime.now(datetime.UTC))
        e.set_image(url=img['url'])
        e.set_author(name="🔭 James Webb Space Telescope")
        await ctx.send(embed=e)
    else: await ctx.send("❌ JWST unavailable.")

@bot.command(name="neo")
async def cmd_neo(ctx):
    async with ctx.typing():
        data=nasa_api("/neo/rest/v1/feed",{
            "start_date":datetime.date.today().isoformat(),
            "end_date":datetime.date.today().isoformat()})
        if data:
            today=datetime.date.today().isoformat()
            neos=data.get("near_earth_objects",{}).get(today,[])
            haz=[n for n in neos if n.get("is_potentially_hazardous_asteroid")]
            e=discord.Embed(title=f"☄️ Near-Earth Objects — {today}",
                            colour=0xff6b00 if haz else 0x00ff88,
                            timestamp=datetime.datetime.now(datetime.UTC))
            e.add_field(name="Total",value=f"`{len(neos)}`",inline=True)
            e.add_field(name="⚠️ Hazardous",value=f"`{len(haz)}`",inline=True)
            await ctx.send(embed=e)
        else: await ctx.send("❌ NEO data unavailable.")

@bot.command(name="planets")
async def cmd_planets(ctx):
    msg=await ctx.send("🪐 Fetching planets from NASA JPL… (~30s)")
    pd={}
    for name,info in PLANETS.items():
        au,km=get_planet_dist(info["id"]); pd[name]={"au":au,"km":km}
        await asyncio.sleep(1)
    e=discord.Embed(title="🪐 Solar System — Live Planet Distances",colour=0xbf5fff,
                    timestamp=datetime.datetime.now(datetime.UTC))
    for name,d in pd.items():
        info=PLANETS[name]; au=d.get("au"); km=d.get("km")
        e.add_field(name=f"{info['emoji']} {name}",
                    value=f"`{au} AU`\n`{km:,.0f} km`" if au else "`Loading…`",inline=True)
    await msg.delete(); await ctx.send(embed=e)

@bot.command(name="empire")
async def cmd_empire(ctx):
    e=discord.Embed(title="⚡ POWER EMPIRE — Commands",colour=0xffcc00)
    e.add_field(name="⚡ Generator",  value="`Discord buttons in panel channel`",inline=False)
    e.add_field(name="🔌 Transformer",value="`Discord buttons in panel channel`",inline=False)
    e.add_field(name="🛰️ Satellite",  value="`!status` `!iss` `!apod` `!neo` `!planets`",inline=False)
    e.add_field(name="🔭 JWST",       value="`!webb`",inline=False)
    await ctx.send(embed=e)

# ══════════════════════════════════════════════════
#  ON READY
# ══════════════════════════════════════════════════
@bot.event
async def on_ready():
    print(f"✅ Power Empire Bot online — {bot.user}")
    await bot.tree.sync()
    bot.add_view(GenPanel())
    bot.add_view(TrfPanel())
    gen_task.start()
    trf_task.start()
    if DATA_CH: sat_task.start()
    if APOD_CH: apod_task.start()
    if JWST_CH: jwst_task.start()
    print("✅ All systems started!")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not set!"); exit(1)
    print("⚡ Power Empire Bot launching...")
    bot.run(BOT_TOKEN)
