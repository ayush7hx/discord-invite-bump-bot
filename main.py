import discord
from discord.ext import commands, tasks
import os
import asyncio
import aiohttp
import time
import random
import string
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guild_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

invite_cache = {}
last_bump_times = {}

# ─────────────────────────────────────────────
#  ALL SUPPORTED BUMP BOTS
#  app_id      -> bot ki pehchaan
#  cmd_name    -> slash command ka naam
#  cooldown_h  -> kitne ghante baad dobara bump hoga
#  keywords    -> bump confirm hone ke baad jo message aata hai usme ye words
# ─────────────────────────────────────────────
BUMP_BOTS = {
    # ── Disboard — /bump — 2h cooldown ──────────────────
    "302050872383242240": {
        "name": "Disboard",
        "cmd_name": "bump",
        "cooldown_h": 2,
        "keywords": ["bump done", "bumped", "server bumped"],
        "bot_int_id": 302050872383242240,
    },
    # ── Discadia — /bump — 1h cooldown ──────────────────
    "1222548162741084311": {
        "name": "Discadia",
        "cmd_name": "bump",
        "cooldown_h": 1,
        "keywords": ["bumped", "bump successful", "server has been bumped"],
        "bot_int_id": 1222548162741084311,
    },
    # ── top.gg — /bump — 12h cooldown ───────────────────
    "264811613708746752": {
        "name": "top.gg",
        "cmd_name": "bump",
        "cooldown_h": 12,
        "keywords": ["bumped", "bump", "voted"],
        "bot_int_id": 264811613708746752,
    },
    # ── Infinity Bot List — /bump — 1h cooldown ──────────
    "716948396455108649": {
        "name": "InfinityBots",
        "cmd_name": "bump",
        "cooldown_h": 1,
        "keywords": ["bumped", "bump successful"],
        "bot_int_id": 716948396455108649,
    },
    # ── Void Bots — /bump — 1h cooldown ─────────────────
    "891226286347366410": {
        "name": "VoidBots",
        "cmd_name": "bump",
        "cooldown_h": 1,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 891226286347366410,
    },
    # ── Discord Bot List — /bump — 2h cooldown ───────────
    "483344858939383808": {
        "name": "DiscordBotList",
        "cmd_name": "bump",
        "cooldown_h": 2,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 483344858939383808,
    },
    # ── Discord.bots.gg — /bump — 6h cooldown ────────────
    "387774921943678977": {
        "name": "Discord.bots.gg",
        "cmd_name": "bump",
        "cooldown_h": 6,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 387774921943678977,
    },
    # ── Discords.com — /bump — 2h cooldown ───────────────
    "1000744996328022076": {
        "name": "Discords.com",
        "cmd_name": "bump",
        "cooldown_h": 2,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 1000744996328022076,
    },
    # ── Discord Services — /bump — 2h cooldown ────────────
    "715652345503596595": {
        "name": "DiscordServices",
        "cmd_name": "bump",
        "cooldown_h": 2,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 715652345503596595,
    },
    # ── Disforge — /bump — 4h cooldown ───────────────────
    "1049617674042007612": {
        "name": "Disforge",
        "cmd_name": "bump",
        "cooldown_h": 4,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 1049617674042007612,
    },
    # ── BotList.me — /bump — 2h cooldown ─────────────────
    "1042166164868968458": {
        "name": "BotList.me",
        "cmd_name": "bump",
        "cooldown_h": 2,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 1042166164868968458,
    },
    # ── Discord Center — /bump — 2h cooldown ─────────────
    "507937324942917634": {
        "name": "DiscordCenter",
        "cmd_name": "bump",
        "cooldown_h": 2,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 507937324942917634,
    },
    # ── DISBOARD Alternatives — Discordlist.gg ────────────
    "846471508198170624": {
        "name": "Discordlist.gg",
        "cmd_name": "bump",
        "cooldown_h": 2,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 846471508198170624,
    },
}

# Guild mein available bump bot commands cache
# { guild_id: { app_id_str: { cmd_id, cmd_version } } }
guild_cmd_cache = {}


def make_nonce():
    ts = int(time.time() * 1000)
    return str((ts << 22) + random.randint(0, 4194303))


def make_session_id():
    return ''.join(random.choices(string.hexdigits.lower(), k=32))


# ─────────────────────────────────────────────
#  STEP 1: Guild ke saare slash commands fetch karo
#  Yahan se pata chalega kaunse bump bots installed hain
# ─────────────────────────────────────────────
async def fetch_guild_bump_commands(guild_id: int):
    """
    Guild ke application command index se saare slash commands fetch karo.
    Sirf wahi bump bots milenge jo server mein add hain.
    """
    token = os.getenv('DISCORD_TOKEN')
    url = f"https://discord.com/api/v10/guilds/{guild_id}/application-command-index"
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
    }

    found = {}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                print(f"[CmdFetch] Failed to fetch commands for guild {guild_id}: {resp.status}")
                return found
            data = await resp.json()

    commands_list = data.get("application_commands", [])
    for cmd in commands_list:
        app_id = str(cmd.get("application_id", ""))
        cmd_name = cmd.get("name", "")
        cmd_id = str(cmd.get("id", ""))
        cmd_version = str(cmd.get("version", cmd_id))

        if app_id in BUMP_BOTS and cmd_name == BUMP_BOTS[app_id]["cmd_name"]:
            found[app_id] = {
                "cmd_id": cmd_id,
                "cmd_version": cmd_version,
                "cmd_name": cmd_name,
                "description": cmd.get("description", "Bump your server!"),
            }
            print(f"[CmdFetch] Found: {BUMP_BOTS[app_id]['name']} (app={app_id}, cmd={cmd_id})")

    return found


# ─────────────────────────────────────────────
#  STEP 2: Slash command trigger karo via HTTP
# ─────────────────────────────────────────────
async def trigger_slash_bump(guild: discord.Guild, channel: discord.TextChannel,
                              app_id: str, cmd_info: dict) -> bool:
    token = os.getenv('DISCORD_TOKEN')
    url = "https://discord.com/api/v10/interactions"

    cmd_id = cmd_info["cmd_id"]
    cmd_version = cmd_info["cmd_version"]
    cmd_name = cmd_info["cmd_name"]
    description = cmd_info.get("description", "Bump your server!")

    payload = {
        "type": 2,
        "application_id": app_id,
        "guild_id": str(guild.id),
        "channel_id": str(channel.id),
        "session_id": make_session_id(),
        "data": {
            "version": cmd_version,
            "id": cmd_id,
            "name": cmd_name,
            "type": 1,
            "options": [],
            "application_command": {
                "id": cmd_id,
                "application_id": app_id,
                "version": cmd_version,
                "default_member_permissions": "0",
                "type": 1,
                "nsfw": False,
                "name": cmd_name,
                "description": description,
                "dm_permission": True,
                "options": []
            },
            "attachments": []
        },
        "nonce": make_nonce()
    }

    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            status = resp.status
            text = await resp.text()
            print(f"[SlashBump] {BUMP_BOTS[app_id]['name']} -> HTTP {status}")
            return status in (200, 204)


async def do_text_bump(channel: discord.TextChannel, command: str):
    try:
        await channel.send(command)
        print(f"[TextBump] Sent '{command}' to #{channel.name}")
        return True
    except Exception as e:
        print(f"[TextBump] Error: {e}")
        return False


# ─────────────────────────────────────────────
#  MAIN AUTO BUMP ENGINE
# ─────────────────────────────────────────────
async def run_all_bumps():
    bump_channel_id = int(os.getenv('BUMP_CHANNEL_ID', 0))
    text_commands_raw = os.getenv('BUMP_TEXT_COMMANDS', '')
    text_commands = [c.strip() for c in text_commands_raw.split(',') if c.strip()]

    for guild in bot.guilds:
        # Bump channel dhundho
        channel = guild.get_channel(bump_channel_id)
        if not channel:
            for ch in guild.text_channels:
                if 'bump' in ch.name.lower():
                    channel = ch
                    break

        if not channel:
            print(f"[AutoBump] No bump channel found in '{guild.name}', skipping.")
            continue

        now = datetime.utcnow()

        # Guild ke commands fetch karo (cache karo taaki baar baar na karein)
        if guild.id not in guild_cmd_cache:
            guild_cmd_cache[guild.id] = await fetch_guild_bump_commands(guild.id)

        available_cmds = guild_cmd_cache[guild.id]

        if not available_cmds:
            print(f"[AutoBump] No supported bump bots found in '{guild.name}'")
        else:
            print(f"[AutoBump] Found {len(available_cmds)} bump bot(s) in '{guild.name}'")

        # ── Saare slash bump bots run karo ───────────────
        for app_id, cmd_info in available_cmds.items():
            bot_info = BUMP_BOTS[app_id]
            bot_name = bot_info["name"]
            cooldown_h = bot_info["cooldown_h"]

            last_t = last_bump_times.get(bot_name)
            cooldown_ok = (last_t is None or now - last_t >= timedelta(hours=cooldown_h))

            if cooldown_ok:
                print(f"[AutoBump] Triggering {bot_name} /{cmd_info['cmd_name']}...")
                success = await trigger_slash_bump(guild, channel, app_id, cmd_info)
                if success:
                    last_bump_times[bot_name] = now
                    await channel.send(
                        f"🚀 **Auto Bumped!** Server bumped on **{bot_name}**!"
                    )
                else:
                    await channel.send(
                        f"⚠️ **{bot_name}** auto-bump failed. Try manually!"
                    )
                await asyncio.sleep(4)  # Bots ke beech thoda wait
            else:
                remaining = timedelta(hours=cooldown_h) - (now - last_t)
                mins = int(remaining.total_seconds() // 60)
                print(f"[AutoBump] {bot_name} cooldown: {mins}m remaining.")

        # ── Text-based bump commands ─────────────────────
        for cmd in text_commands:
            cmd_key = f"text_{cmd}"
            last_t = last_bump_times.get(cmd_key)
            if last_t is None or now - last_t >= timedelta(hours=2):
                success = await do_text_bump(channel, cmd)
                if success:
                    last_bump_times[cmd_key] = now
                await asyncio.sleep(3)


# ─────────────────────────────────────────────
#  SCHEDULED TASK
# ─────────────────────────────────────────────
@tasks.loop(minutes=30)
async def auto_bump_task():
    print(f"[AutoBump] Tick at {datetime.utcnow().strftime('%H:%M:%S UTC')}")
    await run_all_bumps()


@auto_bump_task.before_loop
async def before_auto_bump():
    await bot.wait_until_ready()
    await asyncio.sleep(5)
    # Startup par command cache refresh karo
    for guild in bot.guilds:
        guild_cmd_cache[guild.id] = await fetch_guild_bump_commands(guild.id)
    await run_all_bumps()


# ─────────────────────────────────────────────
#  BUMP DETECTION — jab bump bot confirm kare
# ─────────────────────────────────────────────
@bot.event
async def on_message(message):
    # Check if it's a known bump bot responding
    for app_id, bot_info in BUMP_BOTS.items():
        if message.author.id == bot_info["bot_int_id"]:
            content_to_check = message.content.lower()
            if message.embeds:
                for emb in message.embeds:
                    content_to_check += (emb.description or '').lower()
                    content_to_check += (emb.title or '').lower()

            for kw in bot_info["keywords"]:
                if kw in content_to_check:
                    last_bump_times[bot_info["name"]] = datetime.utcnow()
                    print(f"[BumpDetect] {bot_info['name']} bump confirmed!")
                    break

    await bot.process_commands(message)


# ─────────────────────────────────────────────
#  INVITE TRACKER
# ─────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f'✅ {bot.user} is now online!')

    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="the server 🌙"
        )
    )

    for guild in bot.guilds:
        try:
            invites = await guild.fetch_invites()
            invite_cache[guild.id] = {inv.code: inv for inv in invites}
            print(f'Cached {len(invites)} invites for: {guild.name}')
        except Exception as e:
            print(f'Could not cache invites for {guild.name}: {e}')

    auto_bump_task.start()
    print('🔄 Auto bump task started!')


@bot.event
async def on_invite_create(invite):
    guild_id = invite.guild.id
    if guild_id not in invite_cache:
        invite_cache[guild_id] = {}
    invite_cache[guild_id][invite.code] = invite


@bot.event
async def on_invite_delete(invite):
    guild_id = invite.guild.id
    if guild_id in invite_cache and invite.code in invite_cache[guild_id]:
        del invite_cache[guild_id][invite.code]


@bot.event
async def on_member_join(member):
    guild = member.guild
    inviter = None
    invite_count = 0

    try:
        new_invites = await guild.fetch_invites()
        new_invite_map = {inv.code: inv for inv in new_invites}
        old_invites = invite_cache.get(guild.id, {})

        for code, new_inv in new_invite_map.items():
            old_inv = old_invites.get(code)
            if old_inv is None or new_inv.uses > old_inv.uses:
                if new_inv.inviter:
                    inviter = new_inv.inviter
                    invite_count = new_inv.uses
                break

        invite_cache[guild.id] = new_invite_map
    except Exception as e:
        print(f'Invite tracking error: {e}')

    invite_channel_id = int(os.getenv('INVITE_CHANNEL_ID', 0))
    channel = guild.get_channel(invite_channel_id)

    if not channel:
        print('INVITE_CHANNEL_ID not set or channel not found!')
        return

    if inviter:
        msg = (
            f'{member.mention} has joined **{guild.name}**, '
            f'invited by user **{inviter}**, '
            f'who has now **{invite_count}** invites'
        )
    else:
        msg = (
            f'{member.mention} has joined **{guild.name}**, '
            f'invite link could not be determined'
        )

    await channel.send(msg)


# ─────────────────────────────────────────────
#  COMMANDS
# ─────────────────────────────────────────────
@bot.command(name='invites')
async def check_invites(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    guild = ctx.guild
    try:
        invites = await guild.fetch_invites()
        total = sum(inv.uses for inv in invites if inv.inviter and inv.inviter.id == member.id)
        embed = discord.Embed(
            title='📊 Invite Stats',
            description=f'{member.mention} has **{total}** invite(s)',
            color=0x5865F2
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f'❌ Error: {e}')


@bot.command(name='bumpstatus')
async def bump_status(ctx):
    now = datetime.utcnow()
    lines = []

    available = guild_cmd_cache.get(ctx.guild.id, {})
    for app_id, cmd_info in available.items():
        bot_info = BUMP_BOTS[app_id]
        name = bot_info["name"]
        cooldown_h = bot_info["cooldown_h"]
        last_t = last_bump_times.get(name)

        if last_t is None:
            lines.append(f'✅ **{name}** — Ready to bump!')
        else:
            remaining = timedelta(hours=cooldown_h) - (now - last_t)
            if remaining.total_seconds() <= 0:
                lines.append(f'✅ **{name}** — Ready to bump!')
            else:
                mins = int(remaining.total_seconds() // 60)
                lines.append(f'⏳ **{name}** — {mins}m remaining (cooldown: {cooldown_h}h)')

    if not lines:
        lines = ['⏳ Loading bump bots... Try again in a moment!']

    embed = discord.Embed(
        title='🚀 Auto Bump Status',
        description='\n'.join(lines),
        color=0x5865F2,
        timestamp=now
    )
    embed.set_footer(text='Bot auto-bumps every 2h per platform')
    await ctx.send(embed=embed)


@bot.command(name='forcebump')
@commands.has_permissions(administrator=True)
async def force_bump(ctx):
    await ctx.send('⚡ Force running all bumps now...')
    last_bump_times.clear()
    # Refresh command cache too
    guild_cmd_cache[ctx.guild.id] = await fetch_guild_bump_commands(ctx.guild.id)
    await run_all_bumps()
    await ctx.send('✅ Done!')


@bot.command(name='listbumpbots')
async def list_bump_bots(ctx):
    available = guild_cmd_cache.get(ctx.guild.id, {})
    if not available:
        # Try fetching now
        available = await fetch_guild_bump_commands(ctx.guild.id)
        guild_cmd_cache[ctx.guild.id] = available

    if not available:
        await ctx.send('❌ No supported bump bots found in this server.')
        return

    lines = []
    for app_id, cmd_info in available.items():
        info = BUMP_BOTS[app_id]
        lines.append(f'✅ **{info["name"]}** — `/{cmd_info["cmd_name"]}` — cooldown: {info["cooldown_h"]}h')

    embed = discord.Embed(
        title='🤖 Detected Bump Bots',
        description='\n'.join(lines),
        color=0x57F287
    )
    await ctx.send(embed=embed)


# ─────────────────────────────────────────────
#  HEALTH CHECK SERVER (Render Web Service ke liye)
#  Bot ke saath ek simple HTTP server chalata hai
#  Render ko port milta hai, bot kaam karta hai
# ─────────────────────────────────────────────
from aiohttp import web as aio_web

async def health(request):
    return aio_web.Response(text="✅ Bot is alive!")

async def run_health_server():
    app = aio_web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = aio_web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = aio_web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Health check server running on port {port}")


async def main():
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print('❌ ERROR: DISCORD_TOKEN not set in environment variables!')
        return
    await run_health_server()
    await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
