import os
import json
import datetime
import requests
import discord
from discord.ext import commands, tasks
from pathlib import Path

TOKEN    = os.getenv("DISCORD_TOKEN", "")
JWST_KEY = os.getenv("JWST_API_KEY", "")
JWST_CH  = int(os.getenv("JWST_CHANNEL_ID", "0"))
PREFIX   = "!webb "

# Memory
STATE_FILE = Path("jwst_state.json")

def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except: pass
    return {"last_id": None, "last_date": None}

def save_state(s):
    STATE_FILE.write_text(json.dumps(s, indent=2))

state = load_state()

def get_jwst():
    try:
        r = requests.get(
            "https://api.jwstapi.com/all/type/jpg",
            headers={"X-Api-Key": JWST_KEY},
            timeout=15
        )
        d = r.json()
        if d:
            img = d[0]
            return {
                "id":    img.get("id",""),
                "title": img.get("details",{}).get("mission","JWST"),
                "url":   img.get("file_url",""),
                "desc":  img.get("details",{}).get("description",""),
                "date":  img.get("details",{}).get("date",""),
            }
    except: pass
    return None

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f"🔭 JWST Bot online — {bot.user}")
    daily_jwst.start()

@tasks.loop(hours=24)
async def daily_jwst():
    ch = bot.get_channel(JWST_CH)
    if not ch: return
    today = datetime.date.today().isoformat()
    if state.get("last_date") == today:
        print("⏭️ JWST already sent today")
        return
    img = get_jwst()
    if img and img["id"] != state.get("last_id"):
        e = discord.Embed(
            title=f"🔭 {img['title']}",
            description=img['desc'][:500]+"…",
            colour=0x4b0082,
            timestamp=datetime.datetime.utcnow()
        )
        e.set_image(url=img['url'])
        e.set_author(name="🔭 James Webb Space Telescope")
        e.set_footer(text=f"📅 {img['date']}")
        await ch.send(embed=e)
        state["last_id"]   = img["id"]
        state["last_date"] = today
        save_state(state)
        print(f"🔭 JWST sent — {img['title']}")

@bot.command(name="latest")
async def cmd_latest(ctx):
    img = get_jwst()
    if img:
        e = discord.Embed(
            title=f"🔭 {img['title']}",
            description=img['desc'][:500]+"…",
            colour=0x4b0082,
            timestamp=datetime.datetime.utcnow()
        )
        e.set_image(url=img['url'])
        e.set_author(name="🔭 James Webb Space Telescope")
        e.set_footer(text=f"📅 {img['date']}")
        await ctx.send(embed=e)
    else:
        await ctx.send("❌ JWST unavailable.")

@bot.command(name="help2")
async def cmd_help(ctx):
    e = discord.Embed(
        title="🔭 JWST Bot Commands",
        description=f"Prefix: `{PREFIX}`",
        colour=0x4b0082
    )
    e.add_field(name="`!webb latest`", value="Latest Webb image", inline=True)
    await ctx.send(embed=e)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ No token!"); exit(1)
    print("🔭 JWST Bot launching…")
    bot.run(TOKEN)
