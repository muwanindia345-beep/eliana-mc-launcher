#!/usr/bin/env python3
"""
🛰️ SATELLITE-01 — NASA Space Bot
Add this to your existing Railway deployment.
Uses the SAME Discord token as your other bots.
"""

import os, json, asyncio, random, datetime, requests, discord
from discord.ext import commands, tasks

# ══════════════════════════════════════════════════════
#  CONFIG — reads from Railway environment variables
# ══════════════════════════════════════════════════════
TOKEN    = os.getenv("DISCORD_TOKEN", "")
NASA_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
APOD_CH  = int(os.getenv("APOD_CHANNEL_ID",  "0"))
DATA_CH  = int(os.getenv("DATA_CHANNEL_ID",  "0"))
ALERT_CH = int(os.getenv("ALERT_CHANNEL_ID", "0"))
PREFIX   = os.getenv("SAT_PREFIX", "!sat ")

# ══════════════════════════════════════════════════════
#  SATELLITE TELEMETRY SIMULATOR
# ══════════════════════════════════════════════════════
class Satellite:
    def __init__(self):
        self.alt    = 549.99
        self.batt   = 98.0
        self.solar  = 0.0
        self.hot    = 82.0
        self.cold   = -42.0
        self.orbit  = 1
        self.pkts   = 0
        self.uptime = 0
        self.cpu    = 28.5
        self.signal = 92.0

    def tick(self, s=300):
        self.uptime += s
        self.alt     = round(max(540,min(560,self.alt+random.uniform(-.03,.02))),2)
        h            = datetime.datetime.utcnow().hour
        sun          = 6<=h<=18
        self.solar   = round(random.uniform(1380,1460),1) if sun else 0.0
        self.batt    = round(min(100,self.batt+random.uniform(.1,.6)),1) if sun else round(max(55,self.batt-random.uniform(.1,.4)),1)
        self.hot     = round(random.uniform(75,90),1)
        self.cold    = round(random.uniform(-55,-40),1)
        self.cpu     = round(random.uniform(25,38),1)
        self.signal  = round(random.uniform(85,98),1)
        self.orbit   = (self.uptime//5400)+1
        self.pkts   += random.randint(120,200)

    def uptime_str(self):
        s=self.uptime; d,s=divmod(s,86400); h,s=divmod(s,3600); m,s=divmod(s,60)
        return f"{d}d {h:02d}h {m:02d}m {s:02d}s"

    def status(self):
        if self.batt>80: return "🟢","NOMINAL"
        if self.batt>50: return "🟡","CAUTION"
        return "🔴","CRITICAL"

sat = Satellite()

# ══════════════════════════════════════════════════════
#  8 PLANETS
# ══════════════════════════════════════════════════════
PLANETS = {
    "Mercury":{"id":"199","emoji":"☿"},
    "Venus":  {"id":"299","emoji":"♀"},
    "Earth":  {"id":"399","emoji":"🌍"},
    "Mars":   {"id":"499","emoji":"♂"},
    "Jupiter":{"id":"599","emoji":"♃"},
    "Saturn": {"id":"699","emoji":"♄"},
    "Uranus": {"id":"799","emoji":"⛢"},
    "Neptune":{"id":"899","emoji":"♆"},
}

def get_planet_dist(pid):
    try:
        import re
        today    = datetime.date.today().isoformat()
        tomorrow = (datetime.date.today()+datetime.timedelta(days=1)).isoformat()
        r = requests.get("https://ssd.jpl.nasa.gov/api/horizons.api", params={
            "format":"json","COMMAND":f"'{pid}'","OBJ_DATA":"'NO'",
            "MAKE_EPHEM":"'YES'","EPHEM_TYPE":"'VECTORS'","CENTER":"'500@10'",
            "START_TIME":f"'{today}'","STOP_TIME":f"'{tomorrow}'",
            "STEP_SIZE":"'1 d'","OUT_UNITS":"'AU-D'"
        }, timeout=20)
        txt = r.json().get("result","")
        m   = re.search(r'X\s*=\s*([-\d.E+]+)\s+Y\s*=\s*([-\d.E+]+)\s+Z\s*=\s*([-\d.E+]+)',txt)
        if m:
            x,y,z   = float(m.group(1)),float(m.group(2)),float(m.group(3))
            au       = round((x**2+y**2+z**2)**0.5,4)
            km       = round(au*149597870.7,0)
            return au,km
    except: pass
    return None,None

# ══════════════════════════════════════════════════════
#  NASA HELPERS
# ══════════════════════════════════════════════════════
def nasa(ep, params=None):
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

# ══════════════════════════════════════════════════════
#  EMBEDS
# ══════════════════════════════════════════════════════
def E_telemetry():
    em,st=sat.status(); lat,lon=get_iss()
    e=discord.Embed(title=f"{em} SATELLITE-01 · Live Telemetry",colour=0x00e5ff,timestamp=datetime.datetime.utcnow())
    e.add_field(name="🛰️ Altitude",   value=f"`{sat.alt} km`",        inline=True)
    e.add_field(name="🔋 Battery",    value=f"`{sat.batt}%`",         inline=True)
    e.add_field(name="☀️ Solar",      value=f"`{sat.solar} W`",       inline=True)
    e.add_field(name="🌡️ Hot Side",   value=f"`+{sat.hot}°C`",       inline=True)
    e.add_field(name="❄️ Cold Side",  value=f"`{sat.cold}°C`",       inline=True)
    e.add_field(name="💻 CPU",        value=f"`{sat.cpu}°C`",         inline=True)
    e.add_field(name="📡 Signal",     value=f"`{sat.signal}%`",       inline=True)
    e.add_field(name="🔄 Orbit #",    value=f"`{sat.orbit}`",         inline=True)
    e.add_field(name="📦 Packets",    value=f"`{sat.pkts:,}`",        inline=True)
    e.add_field(name="⏱️ Uptime",     value=f"`{sat.uptime_str()}`", inline=True)
    e.add_field(name="✅ Status",     value=f"`{st}`",                inline=True)
    e.add_field(name="📐 Incl.",      value="`53.05°`",               inline=True)
    if lat: e.add_field(name="🚀 ISS",value=f"`Lat {lat:+.3f}°  Lon {lon:+.3f}°`",inline=False)
    e.set_author(name="🛰️ SATELLITE-01 · Ground Station · LEO 550km")
    e.set_footer(text=f"🕐 {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    return e

def E_apod(d):
    e=discord.Embed(title=f"🌌 {d.get('title','')}",url=d.get("url",""),
      description=(d.get("explanation","")[:900]+"…"),colour=0x1a1040,timestamp=datetime.datetime.utcnow())
    if d.get("media_type")=="image": e.set_image(url=d.get("hdurl") or d.get("url",""))
    e.set_author(name="🛰️ SATELLITE-01 · NASA APOD")
    e.set_footer(text=f"📅 {d.get('date','')}  ·  © {d.get('copyright','NASA')}")
    return e

def E_neo(data):
    today=datetime.date.today().isoformat()
    neos=data.get("near_earth_objects",{}).get(today,[])
    haz=[n for n in neos if n.get("is_potentially_hazardous_asteroid")]
    e=discord.Embed(title=f"☄️ Near-Earth Objects — {today}",
      colour=0xff6b00 if haz else 0x00ff88,timestamp=datetime.datetime.utcnow())
    e.add_field(name="Total",value=f"`{len(neos)}`",inline=True)
    e.add_field(name="⚠️ Hazardous",value=f"`{len(haz)}`",inline=True)
    for neo in neos[:4]:
        cd=neo.get("close_approach_data",[{}])[0]
        dist=cd.get("miss_distance",{}).get("kilometers","N/A")
        vel=cd.get("relative_velocity",{}).get("kilometers_per_hour","N/A")
        dm=neo.get("estimated_diameter",{}).get("kilometers",{})
        flag="⚠️" if neo.get("is_potentially_hazardous_asteroid") else "✅"
        try: df=f"{float(dist):,.0f} km"; vf=f"{float(vel):,.0f} km/h"
        except: df=str(dist); vf=str(vel)
        e.add_field(name=f"{flag} {neo['name']}",
          value=f"Miss: `{df}`\nSpeed: `{vf}`",inline=True)
    e.set_author(name="🛰️ SATELLITE-01 · Asteroid Watch")
    return e

def E_iss(lat,lon,crew):
    e=discord.Embed(title="🚀 ISS Live Position + Crew",colour=0x00e5ff,timestamp=datetime.datetime.utcnow())
    e.add_field(name="📍 Lat",value=f"`{lat:+.4f}°`",inline=True)
    e.add_field(name="📍 Lon",value=f"`{lon:+.4f}°`",inline=True)
    e.add_field(name="🛸 Alt",value="`~408 km`",inline=True)
    e.add_field(name="⚡ Speed",value="`7.66 km/s`",inline=True)
    e.add_field(name="🗺️ Map",value=f"[View](https://www.google.com/maps?q={lat},{lon}&z=4)",inline=True)
    if crew:
        e.add_field(name=f"👨‍🚀 Crew ({crew.get('number',0)})",
          value="\n".join(f"• {p['name']} ({p['craft']})" for p in crew.get("people",[])),inline=False)
    e.set_author(name="🛰️ SATELLITE-01 · ISS Tracker")
    return e

def E_earth(url,date):
    e=discord.Embed(title="🌍 Earth From Space — NASA EPIC",colour=0x0044aa,
      description="Photo from DSCOVR at L1 Lagrange point — 1.5 million km away.",timestamp=datetime.datetime.utcnow())
    e.set_image(url=url)
    e.set_footer(text=f"📅 {date}")
    e.set_author(name="🛰️ SATELLITE-01 · Earth Observation")
    return e

def E_planets(pdata):
    e=discord.Embed(title="🪐 Solar System — Live Planet Distances",colour=0xbf5fff,timestamp=datetime.datetime.utcnow())
    for name,d in pdata.items():
        info=PLANETS[name]; au=d.get("au"); km=d.get("km")
        e.add_field(name=f"{info['emoji']} {name}",
          value=f"`{au} AU`\n`{km:,.0f} km`" if au else "`Loading…`",inline=True)
    e.set_author(name="🛰️ SATELLITE-01 · NASA JPL Horizons")
    e.set_footer(text="1 AU = 149,597,870 km · Real orbital data")
    return e

def E_flares(fl):
    e=discord.Embed(title="☀️ Solar Flare Activity — 72hrs",colour=0xffd600,timestamp=datetime.datetime.utcnow())
    if not fl: e.description="✅ No significant solar flares detected."
    else:
        for f in fl[:5]:
            e.add_field(name=f"🔥 Class {f.get('classType','?')} — {f.get('beginTime','')[:10]}",
              value=f"Peak: `{f.get('peakTime','N/A')}`\nSource: `{f.get('sourceLocation','?')}`",inline=True)
    e.set_author(name="🛰️ SATELLITE-01 · Space Weather")
    return e

# ══════════════════════════════════════════════════════
#  BOT
# ══════════════════════════════════════════════════════
intents=discord.Intents.default(); intents.message_content=True
bot=commands.Bot(command_prefix=PREFIX,intents=intents)

@bot.event
async def on_ready():
    print(f"🛰️  SATELLITE-01 online — {bot.user}")
    tele_loop.start(); apod_loop.start()
    neo_loop.start();  epic_loop.start(); planet_loop.start()

@tasks.loop(minutes=5)
async def tele_loop():
    ch=bot.get_channel(DATA_CH)
    if not ch: return
    sat.tick(300); await ch.send(embed=E_telemetry())

@tasks.loop(hours=1)
async def apod_loop():
    ch=bot.get_channel(APOD_CH)
    if not ch: return
    d=nasa("/planetary/apod")
    if d and "title" in d: await ch.send(embed=E_apod(d))

@tasks.loop(hours=24)
async def neo_loop():
    ch=bot.get_channel(ALERT_CH)
    if not ch: return
    data=nasa("/neo/rest/v1/feed",{"start_date":datetime.date.today().isoformat(),"end_date":datetime.date.today().isoformat()})
    if data: await ch.send(embed=E_neo(data))
    fl=nasa("/DONKI/FLR",{"startDate":(datetime.date.today()-datetime.timedelta(days=3)).isoformat(),"endDate":datetime.date.today().isoformat()})
    if fl is not None: await ch.send(embed=E_flares(fl))

@tasks.loop(hours=6)
async def epic_loop():
    ch=bot.get_channel(APOD_CH)
    if not ch: return
    url,date=get_epic()
    if url: await ch.send(embed=E_earth(url,date))

@tasks.loop(hours=12)
async def planet_loop():
    ch=bot.get_channel(DATA_CH)
    if not ch: return
    pd={}
    for name,info in PLANETS.items():
        au,km=get_planet_dist(info["id"]); pd[name]={"au":au,"km":km}; await asyncio.sleep(1)
    await ch.send(embed=E_planets(pd))

# ── COMMANDS ──
@bot.command(name="status",aliases=["tele","telemetry"])
async def cmd_status(ctx):
    sat.tick(60); await ctx.send(embed=E_telemetry())

@bot.command(name="apod")
async def cmd_apod(ctx):
    async with ctx.typing():
        d=nasa("/planetary/apod")
    if d and "title" in d: await ctx.send(embed=E_apod(d))
    else: await ctx.send("❌ APOD unavailable.")

@bot.command(name="iss")
async def cmd_iss(ctx):
    lat,lon=get_iss(); crew=get_crew()
    if lat: await ctx.send(embed=E_iss(lat,lon,crew))
    else: await ctx.send("❌ ISS tracker offline.")

@bot.command(name="neo",aliases=["asteroids"])
async def cmd_neo(ctx):
    async with ctx.typing():
        data=nasa("/neo/rest/v1/feed",{"start_date":datetime.date.today().isoformat(),"end_date":datetime.date.today().isoformat()})
    if data: await ctx.send(embed=E_neo(data))
    else: await ctx.send("❌ NEO data unavailable.")

@bot.command(name="earth",aliases=["epic"])
async def cmd_earth(ctx):
    async with ctx.typing():
        url,date=get_epic()
    if url: await ctx.send(embed=E_earth(url,date))
    else: await ctx.send("❌ EPIC unavailable.")

@bot.command(name="planets",aliases=["solar"])
async def cmd_planets(ctx):
    msg=await ctx.send("🪐 Fetching all 8 planets from NASA JPL… (~30 sec)")
    pd={}
    async with ctx.typing():
        for name,info in PLANETS.items():
            au,km=get_planet_dist(info["id"]); pd[name]={"au":au,"km":km}; await asyncio.sleep(1)
    await msg.delete(); await ctx.send(embed=E_planets(pd))

@bot.command(name="weather",aliases=["flares"])
async def cmd_weather(ctx):
    async with ctx.typing():
        fl=nasa("/DONKI/FLR",{"startDate":(datetime.date.today()-datetime.timedelta(days=3)).isoformat(),"endDate":datetime.date.today().isoformat()})
    await ctx.send(embed=E_flares(fl or []))

@bot.command(name="crew",aliases=["astronauts"])
async def cmd_crew(ctx):
    data=get_crew()
    if data:
        e=discord.Embed(title=f"👨‍🚀 {data['number']} Humans in Space",colour=0x00e5ff,timestamp=datetime.datetime.utcnow())
        by={}
        for p in data["people"]: by.setdefault(p["craft"],[]).append(p["name"])
        for craft,names in by.items():
            e.add_field(name=f"🚀 {craft}",value="\n".join(f"• {n}" for n in names),inline=False)
        e.set_author(name="🛰️ SATELLITE-01")
        await ctx.send(embed=e)
    else: await ctx.send("❌ Crew data unavailable.")

@bot.command(name="help2",aliases=["commands","menu"])
async def cmd_help(ctx):
    e=discord.Embed(title="🛰️ SATELLITE-01 Commands",description=f"Prefix: `{PREFIX}`",colour=0x00e5ff)
    for cmd,desc in [("status","📡 Live telemetry"),("apod","🌌 NASA picture of the day"),
      ("iss","🚀 ISS position + crew"),("neo","☄️ Asteroids today"),
      ("earth","🌍 NASA EPIC Earth photo"),("planets","🪐 All 8 planets from JPL"),
      ("weather","☀️ Solar flares"),("crew","👨‍🚀 Humans in space")]:
        e.add_field(name=f"`{PREFIX}{cmd}`",value=desc,inline=True)
    e.set_footer(text="Auto: telemetry 5min · APOD hourly · NEO daily · Planets 12hrs")
    await ctx.send(embed=e)

if __name__=="__main__":
    if not TOKEN: print("❌ DISCORD_TOKEN not set!"); exit(1)
    print("🛰️  Launching SATELLITE-01…")
    bot.run(TOKEN)
