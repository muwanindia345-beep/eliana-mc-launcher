# bio_feed.py
import os, requests, datetime, random
import discord
from discord.ext import tasks
from discord import app_commands

# ══════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════
BIO_FEED_CH    = int(os.getenv("BIO_FEED_CH",   "1505982538844471466"))
BIO_ALERT_CH   = int(os.getenv("BIO_ALERT_CH",  "1505982738392682617"))
BIO_ADMIN_ROLE = int(os.getenv("BIO_ADMIN_ROLE","1505983083328049253"))

_bot      = None
_feed_msg = None

# ══════════════════════════════════════════════════
#  ROLE CHECK
# ══════════════════════════════════════════════════
def is_bio_admin(interaction: discord.Interaction) -> bool:
    return any(r.id == BIO_ADMIN_ROLE for r in interaction.user.roles)

# ══════════════════════════════════════════════════
#  API FUNCTIONS
# ══════════════════════════════════════════════════
def fetch_who_outbreaks():
    try:
        r = requests.get(
            "https://www.who.int/api/news/diseaseoutbreaknews",
            timeout=15
        )
        return r.json().get("value", [])[:3]
    except:
        return []

def fetch_ncbi_virus(query="coronavirus"):
    try:
        search = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={
                "db": "nucleotide", "term": f"{query}[organism]",
                "retmax": 5, "sort": "date", "retmode": "json"
            }, timeout=15
        )
        ids = search.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return None

        summary = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={"db": "nucleotide", "id": ",".join(ids[:3]), "retmode": "json"},
            timeout=15
        )
        result = summary.json().get("result", {})
        entries = []
        for uid in ids[:3]:
            item = result.get(uid, {})
            if item:
                entries.append({
                    "title":     item.get("title", "Unknown"),
                    "accession": item.get("accessionversion", "N/A"),
                    "length":    item.get("slen", 0),
                    "organism":  item.get("organism", "Unknown"),
                    "date":      item.get("updatedate", "N/A")
                })
        return entries
    except:
        return None

def fetch_endangered():
    try:
        r = requests.get(
            "https://api.gbif.org/v1/species/search",
            params={"threatStatus": "ENDANGERED", "limit": 5,
                    "offset": random.randint(0, 50)},
            timeout=15
        )
        return r.json().get("results", [])[:5]
    except:
        return []

# ══════════════════════════════════════════════════
#  BLOOD AMBIENT FEED EMBED
# ══════════════════════════════════════════════════
PARTICLES = ["🩸","💉","🧬","🦠","⚗️","🔬","☣️","🧫"]

def blood_feed_embed():
    now        = datetime.datetime.now(datetime.UTC)
    particles  = "  ".join(random.choices(PARTICLES, k=7))
    outbreaks  = fetch_who_outbreaks()
    species    = fetch_endangered()

    e = discord.Embed(
        title="🩸 BLOODYLUCIA — BIO INTELLIGENCE FEED",
        description=(
            f"```\n{'─'*36}\n"
            f"  BIOLOGICAL SURVEILLANCE STREAM\n"
            f"{'─'*36}```\n{particles}"
        ),
        color=0x8b0000,
        timestamp=now
    )

    # WHO Outbreaks
    if outbreaks:
        txt = ""
        for o in outbreaks[:2]:
            title = o.get("title", "Unknown")[:55]
            date  = o.get("publishedDate", "")[:10]
            txt  += f"• {title}\n  `{date}`\n"
        e.add_field(name="🦠 WHO — ACTIVE OUTBREAKS", value=txt, inline=False)
    else:
        e.add_field(name="🦠 WHO — ACTIVE OUTBREAKS",
                    value="```Scanning global databases...```", inline=False)

    # Extinction Tracker
    if species:
        txt = ""
        for s in species[:3]:
            name    = s.get("canonicalName", "Unknown")
            kingdom = s.get("kingdom", "?")
            txt    += f"• *{name}*  `{kingdom}`\n"
        e.add_field(name="💀 EXTINCTION TRACKER", value=txt, inline=False)
    else:
        e.add_field(name="💀 EXTINCTION TRACKER",
                    value="```Loading species data...```", inline=False)

    e.add_field(
        name="🔐 ACCESS LEVELS",
        value="```Bio Administration 🧬 — Full terminal\nObservers           — Read only stream```",
        inline=False
    )
    e.set_footer(text="🩸 BloodyLucia • WHO • NCBI • GBIF • Classified")
    return e

# ══════════════════════════════════════════════════
#  BACKGROUND TASKS
# ══════════════════════════════════════════════════
@tasks.loop(minutes=30)
async def blood_feed_task():
    global _feed_msg
    ch = _bot.get_channel(BIO_FEED_CH)
    if not ch:
        return
    try:
        embed = blood_feed_embed()
        if _feed_msg:
            await _feed_msg.edit(embed=embed)
        else:
            _feed_msg = await ch.send(embed=embed)
    except Exception as ex:
        print(f"[BIO] Feed error: {ex}")

@tasks.loop(hours=6)
async def who_alert_task():
    ch = _bot.get_channel(BIO_ALERT_CH)
    if not ch:
        return
    try:
        outbreaks = fetch_who_outbreaks()
        if not outbreaks:
            return
        e = discord.Embed(
            title="🚨 WHO — DISEASE OUTBREAK ALERT",
            color=0xff0000,
            timestamp=datetime.datetime.now(datetime.UTC)
        )
        for o in outbreaks[:3]:
            title = o.get("title", "Unknown")[:80]
            date  = o.get("publishedDate", "N/A")[:10]
            e.add_field(name=f"🦠 {title}", value=f"`Reported: {date}`", inline=False)
        e.set_footer(text="Source: WHO Disease Outbreak News")
        await ch.send(embed=e)
    except Exception as ex:
        print(f"[BIO] Alert error: {ex}")

# ══════════════════════════════════════════════════
#  SLASH COMMANDS
# ══════════════════════════════════════════════════
async def setup(bot):
    global _bot
    _bot = bot

    # ── /genome ──────────────────────────────────
    @bot.tree.command(name="genome",
                      description="🧬 Search NCBI — National Center for Biotechnology Information")
    @app_commands.describe(query="Virus or organism name (e.g. coronavirus, influenza)")
    async def genome(interaction: discord.Interaction, query: str):
        if not is_bio_admin(interaction):
            await interaction.response.send_message(
                "🔐 **Bio Administration 🧬** only!", ephemeral=True); return

        await interaction.response.defer()
        results = fetch_ncbi_virus(query)
        if not results:
            await interaction.followup.send("❌ No genome data found.", ephemeral=True); return

        e = discord.Embed(
            title=f"🧬 NCBI GENOME — {query.upper()}",
            description="**National Center for Biotechnology Information**",
            color=0x8b0000,
            timestamp=datetime.datetime.now(datetime.UTC)
        )
        for r in results:
            e.add_field(
                name=f"🔬 {r['accession']}",
                value=(f"```"
                       f"Organism : {r['organism']}\n"
                       f"Length   : {r['length']} bp\n"
                       f"Updated  : {r['date']}\n\n"
                       f"{r['title'][:80]}```"),
                inline=False
            )
        e.set_footer(text="NCBI Nucleotide Database • Restricted Access 🔐")
        await interaction.followup.send(embed=e)

    # ── /outbreak ────────────────────────────────
    @bot.tree.command(name="outbreak",
                      description="🦠 WHO — World Health Organization live outbreak data")
    async def outbreak(interaction: discord.Interaction):
        if not is_bio_admin(interaction):
            await interaction.response.send_message(
                "🔐 **Bio Administration 🧬** only!", ephemeral=True); return

        await interaction.response.defer()
        outbreaks = fetch_who_outbreaks()
        if not outbreaks:
            await interaction.followup.send("❌ No outbreak data available.", ephemeral=True); return

        e = discord.Embed(
            title="🦠 WHO — LIVE OUTBREAK INTELLIGENCE",
            description="**World Health Organization — Disease Outbreak News**",
            color=0xff4400,
            timestamp=datetime.datetime.now(datetime.UTC)
        )
        for o in outbreaks[:5]:
            title = o.get("title", "Unknown")[:80]
            date  = o.get("publishedDate", "N/A")[:10]
            e.add_field(name=f"⚠️ {title}", value=f"`Date: {date}`", inline=False)
        e.set_footer(text="WHO Disease Outbreak News • Bio Administration Only 🔐")
        await interaction.followup.send(embed=e)

    # ── /extinction ──────────────────────────────
    @bot.tree.command(name="extinction",
                      description="💀 GBIF — Global Biodiversity Information Facility tracker")
    async def extinction(interaction: discord.Interaction):
        if not is_bio_admin(interaction):
            await interaction.response.send_message(
                "🔐 **Bio Administration 🧬** only!", ephemeral=True); return

        await interaction.response.defer()
        species = fetch_endangered()
        if not species:
            await interaction.followup.send("❌ Species data unavailable.", ephemeral=True); return

        e = discord.Embed(
            title="💀 EXTINCTION TRACKER — ENDANGERED SPECIES",
            description="**GBIF — Global Biodiversity Information Facility**",
            color=0x4a0000,
            timestamp=datetime.datetime.now(datetime.UTC)
        )
        for s in species[:5]:
            name    = s.get("canonicalName", "Unknown")
            kingdom = s.get("kingdom", "Unknown")
            phylum  = s.get("phylum",  "Unknown")
            e.add_field(
                name=f"🔴 {name}",
                value=(f"```Kingdom : {kingdom}\n"
                       f"Phylum  : {phylum}\n"
                       f"Status  : ENDANGERED```"),
                inline=True
            )
        e.set_footer(text="GBIF Biodiversity Database • Bio Administration Only 🔐")
        await interaction.followup.send(embed=e)

    # ── /dna ─────────────────────────────────────
    @bot.tree.command(name="dna",
                      description="🔬 DNA sequence analyzer — composition, complement, GC content")
    @app_commands.describe(sequence="Enter DNA sequence using A, T, G, C only")
    async def dna(interaction: discord.Interaction, sequence: str):
        if not is_bio_admin(interaction):
            await interaction.response.send_message(
                "🔐 **Bio Administration 🧬** only!", ephemeral=True); return

        seq   = sequence.upper().replace(" ", "")
        valid = all(c in "ATGC" for c in seq)
        if not valid:
            await interaction.response.send_message(
                "❌ Invalid sequence! Only **A T G C** allowed.", ephemeral=True); return

        a, t, g, c = seq.count("A"), seq.count("T"), seq.count("G"), seq.count("C")
        total = len(seq)
        gc    = round((g + c) / total * 100, 2)
        at    = round((a + t) / total * 100, 2)

        comp_map    = str.maketrans("ATGC", "TACG")
        complement  = seq.translate(comp_map)
        reverse_comp = complement[::-1]

        e = discord.Embed(
            title="🔬 DNA SEQUENCE ANALYZER",
            color=0x8b0000,
            timestamp=datetime.datetime.now(datetime.UTC)
        )
        e.add_field(name="📊 LENGTH",     value=f"`{total} bp`", inline=True)
        e.add_field(name="🧬 GC CONTENT", value=f"`{gc}%`",      inline=True)
        e.add_field(name="🔗 AT CONTENT", value=f"`{at}%`",      inline=True)
        e.add_field(
            name="📈 BASE COMPOSITION",
            value=(f"```A: {a} ({round(a/total*100,1)}%)   "
                   f"T: {t} ({round(t/total*100,1)}%)\n"
                   f"G: {g} ({round(g/total*100,1)}%)   "
                   f"C: {c} ({round(c/total*100,1)}%)```"),
            inline=False
        )
        e.add_field(
            name="🔄 STRAND ANALYSIS",
            value=(f"```5'→3'  : {seq[:45]}{'...' if total>45 else ''}\n"
                   f"3'→5'  : {complement[:45]}{'...' if total>45 else ''}\n"
                   f"RevCom : {reverse_comp[:45]}{'...' if total>45 else ''}```"),
            inline=False
        )
        e.set_footer(text="BloodyLucia Bio Lab • DNA Analysis Engine 🔐")
        await interaction.response.send_message(embed=e)

    # Start background tasks
    blood_feed_task.start()
    who_alert_task.start()
    print("🧬 [BioFeed] Module loaded!")
