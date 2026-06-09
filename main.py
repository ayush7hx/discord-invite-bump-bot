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
# ─────────────────────────────────────────────
BUMP_BOTS = {
    "302050872383242240": {
        "name": "Disboard",
        "cmd_name": "bump",
        "cmd_id": None,
        "cooldown_h": 2,
        "keywords": ["bump done", "bumped", "server bumped"],
        "bot_int_id": 302050872383242240,
    },
    "1222548162741084311": {
        "name": "Discadia",
        "cmd_name": "bump",
        "cmd_id": None,
        "cooldown_h": 1,
        "keywords": ["bumped", "bump successful", "server has been bumped"],
        "bot_int_id": 1222548162741084311,
    },
    "264811613708746752": {
        "name": "top.gg",
        "cmd_name": "bump",
        "cmd_id": None,
        "cooldown_h": 12,
        "keywords": ["bumped", "bump", "voted"],
        "bot_int_id": 264811613708746752,
    },
    "716948396455108649": {
        "name": "InfinityBots",
        "cmd_name": "bump",
        "cmd_id": None,
        "cooldown_h": 1,
        "keywords": ["bumped", "bump successful"],
        "bot_int_id": 716948396455108649,
    },
    "891226286347366410": {
        "name": "VoidBots",
        "cmd_name": "bump",
        "cmd_id": None,
        "cooldown_h": 1,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 891226286347366410,
    },
    "483344858939383808": {
        "name": "DiscordBotList",
        "cmd_name": "bump",
        "cmd_id": None,
        "cooldown_h": 2,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 483344858939383808,
    },
    "387774921943678977": {
        "name": "Discord.bots.gg",
        "cmd_name": "bump",
        "cmd_id": None,
        "cooldown_h": 6,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 387774921943678977,
    },
    "1000744996328022076": {
        "name": "Discords.com",
        "cmd_name": "bump",
        "cmd_id": None,
        "cooldown_h": 2,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 1000744996328022076,
    },
    "715652345503596595": {
        "name": "DiscordServices",
        "cmd_name": "bump",
        "cmd_id": None,
        "cooldown_h": 2,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 715652345503596595,
    },
    "1049617674042007612": {
        "name": "Disforge",
        "cmd_name": "bump",
        "cmd_id": None,
        "cooldown_h": 4,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 1049617674042007612,
    },
    "1042166164868968458": {
        "name": "BotList.me",
        "cmd_name": "bump",
        "cmd_id": None,
        "cooldown_h": 2,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 1042166164868968458,
    },
    "507937324942917634": {
        "name": "DiscordCenter",
        "cmd_name": "bump",
        "cmd_id": None,
        "cooldown_h": 2,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 507937324942917634,
    },
    "846471508198170624": {
        "name": "Discordlist.gg",
        "cmd_name": "bump",
        "cmd_id": None,
        "cooldown_h": 2,
        "keywords": ["bumped", "bump"],
        "bot_int_id": 846471508198170624,
    },
    "235148962103951360": {
        "name": "Carl-bot",
        "cmd_name": "bump",
        "cmd_id": None,
        "cooldown_h": 24,
        "keywords": ["bumped", "bump", "carl.gg"],
        "bot_int_id": 235148962103951360,
    },
}

guild_cmd_cache = {}
cmd_id_cache = {}  # Cache for fetched command IDs


def make_nonce():
    ts = int(time.time() * 1000)
    return str((ts << 22) + random.randint(0, 4194303))


def make_session_id():
    return ''.join(random.choices(string.hexdigits.lower(), k=32))


def get_user_token():
    """USER_TOKEN fetch karo."""
    token = os.getenv('USER_TOKEN', '').strip().strip('"').strip("'")
    if not token:
        return None
    return token


def get_browser_headers(token: str) -> dict:
    return {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Discord-Locale": "en-US",
        "X-Discord-Timezone": "Asia/Kolkata",
    }


async def fetch_cmd_id_from_api(guild_id: int, app_id: str, cmd_name: str) -> str | None:
    """Discord API se command ID fetch karo."""
    # Check cache first
    cache_key = f"{guild_id}_{app_id}_{cmd_name}"
    if cache_key in cmd_id_cache:
        print(f"[CmdFetch] 💾 Using cached cmd_id for {cmd_name}")
        return cmd_id_cache[cache_key]
    
    user_token = get_user_token()
    if not user_token:
        print(f"[CmdFetch] ❌ USER_TOKEN not set!")
        return None
    
    url = f"https://discord.com/api/v9/guilds/{guild_id}/application-command-index"
    headers = get_browser_headers(user_token)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    print(f"[CmdFetch] ❌ API returned {resp.status}")
                    return None
                
                data = await resp.json()
                all_cmds = data.get("application_commands", []) or data.get("commands", []) or []
                
                for cmd in all_cmds:
                    if (str(cmd.get("application_id")) == app_id and cmd.get("name") == cmd_name):
                        cmd_id = str(cmd["id"])
                        cmd_id_cache[cache_key] = cmd_id  # Cache it
                        print(f"[CmdFetch] ✅ Found cmd_id={cmd_id} for {cmd_name}")
                        return cmd_id
                
                print(f"[CmdFetch] ⚠️ Command {cmd_name} for app {app_id} not found")
    except asyncio.TimeoutError:
        print(f"[CmdFetch] ⏱️ Timeout fetching cmd_id")
    except Exception as e:
        print(f"[CmdFetch] ❌ Error: {e}")
    
    return None


async def fetch_guild_bump_commands(guild: discord.Guild):
    """Guild mein available bump bots detect karo."""
    found = {}
    
    for app_id, bot_info in BUMP_BOTS.items():
        member = guild.get_member(bot_info["bot_int_id"])
        if member is not None:
            cmd_id = bot_info["cmd_id"]
            
            # Agar cmd_id None hai, dynamically fetch karo
            if cmd_id is None:
                print(f"[BotDetect] 🔍 Fetching cmd_id for {bot_info['name']}...")
                cmd_id = await fetch_cmd_id_from_api(guild.id, app_id, bot_info["cmd_name"])
                if cmd_id is None:
                    print(f"[BotDetect] ⚠️ Skip: Could not get cmd_id for {bot_info['name']}")
                    continue
            
            found[app_id] = {
                "cmd_id": cmd_id,
                "cmd_version": cmd_id,
                "cmd_name": bot_info["cmd_name"],
                "description": f"Bump on {bot_info['name']}!",
            }
            print(f"[BotDetect] ✅ {bot_info['name']} ready (cmd_id={cmd_id})")
    
    return found


async def trigger_slash_bump(guild: discord.Guild, channel: discord.TextChannel,
                             app_id: str, cmd_info: dict) -> bool:
    """Slash command trigger karo."""
    user_token = get_user_token()
    if not user_token:
        print(f"[SlashBump] ❌ USER_TOKEN not set!")
        return False
    
    url = "https://discord.com/api/v9/interactions"
    cmd_id = cmd_info["cmd_id"]
    cmd_version = cmd_info["cmd_version"]
    cmd_name = cmd_info["cmd_name"]
    
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
                "description": "Bump!",
                "dm_permission": True,
                "options": []
            },
            "attachments": []
        },
        "nonce": make_nonce()
    }
    
    headers = get_browser_headers(user_token)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                status = resp.status
                
                if status in (200, 204):
                    print(f"[SlashBump] ✅ {BUMP_BOTS[app_id]['name']} triggered successfully")
                    return True
                else:
                    text = await resp.text()
                    print(f"[SlashBump] ❌ {BUMP_BOTS[app_id]['name']} failed (HTTP {status})")
                    if status == 401:
                        print(f"[SlashBump] 🔑 Unauthorized - Check USER_TOKEN!")
                    elif status == 403:
                        print(f"[SlashBump] 🚫 Forbidden - Missing permissions!")
                    return False
    except asyncio.TimeoutError:
        print(f"[SlashBump] ⏱️ Timeout: {BUMP_BOTS[app_id]['name']}")
        return False
    except Exception as e:
        print(f"[SlashBump] ❌ Error: {e}")
        return False


async def do_text_bump(channel: discord.TextChannel, command: str):
    """Text-based bump command."""
    try:
        await channel.send(command)
        print(f"[TextBump] ✅ Sent '{command}' to #{channel.name}")
        return True
    except Exception as e:
        print(f"[TextBump] ❌ Error: {e}")
        return False


async def run_all_bumps():
    """Main auto bump engine."""
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
            print(f"[AutoBump] ⚠️ No bump channel in '{guild.name}'")
            continue
        
        now = datetime.utcnow()
        
        # Guild ke commands fetch karo
        if guild.id not in guild_cmd_cache:
            print(f"[AutoBump] 🔄 Refreshing commands for {guild.name}...")
            guild_cmd_cache[guild.id] = await fetch_guild_bump_commands(guild)
        
        available_cmds = guild_cmd_cache[guild.id]
        
        if not available_cmds:
            print(f"[AutoBump] ⚠️ No bump bots found in '{guild.name}'")
            continue
        
        print(f"[AutoBump] 📊 {len(available_cmds)} bot(s) in '{guild.name}'")
        
        # Saare slash bump bots run karo
        for app_id, cmd_info in available_cmds.items():
            bot_info = BUMP_BOTS[app_id]
            bot_name = bot_info["name"]
            cooldown_h = bot_info["cooldown_h"]
            
            last_t = last_bump_times.get(bot_name)
            cooldown_ok = (last_t is None or now - last_t >= timedelta(hours=cooldown_h))
            
            if cooldown_ok:
                print(f"[AutoBump] 🚀 Triggering {bot_name}...")
                success = await trigger_slash_bump(guild, channel, app_id, cmd_info)
                if success:
                    last_bump_times[bot_name] = now
                    embed = discord.Embed(
                        title="✅ Auto Bump Successful!",
                        description=f"Server bumped on **{bot_name}**",
                        color=0x57F287
                    )
                    await channel.send(embed=embed)
                else:
                    embed = discord.Embed(
                        title="⚠️ Auto Bump Failed!",
                        description=f"**{bot_name}** failed. Try manually!",
                        color=0xED4245
                    )
                    await channel.send(embed=embed)
                await asyncio.sleep(4)
            else:
                remaining = timedelta(hours=cooldown_h) - (now - last_t)
                mins = int(remaining.total_seconds() // 60)
                print(f"[AutoBump] ⏳ {bot_name}: {mins}m cooldown remaining")
        
        # Text-based bump commands
        for cmd in text_commands:
            cmd_key = f"text_{cmd}"
            last_t = last_bump_times.get(cmd_key)
            if last_t is None or now - last_t >= timedelta(hours=2):
                success = await do_text_bump(channel, cmd)
                if success:
                    last_bump_times[cmd_key] = now
                await asyncio.sleep(3)


@tasks.loop(minutes=30)
async def auto_bump_task():
    """Every 30 minutes auto bump."""
    print(f"\n[AutoBump] ⏰ Task tick at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    await run_all_bumps()


@auto_bump_task.before_loop
async def before_auto_bump():
    """Setup before auto bump."""
    await bot.wait_until_ready()
    await asyncio.sleep(5)
    print("[AutoBump] 🔄 Initial setup...")
    for guild in bot.guilds:
        guild_cmd_cache[guild.id] = await fetch_guild_bump_commands(guild)
    await run_all_bumps()


@bot.event
async def on_message(message):
    """Detect bump bot confirmations."""
    # Ignore bot's own messages
    if message.author == bot.user:
        return
    
    for app_id, bot_info in BUMP_BOTS.items():
        if message.author.id == bot_info["bot_int_id"]:
            content_to_check = message.content.lower()
            
            # Check embeds too
            if message.embeds:
                for emb in message.embeds:
                    if emb.description:
                        content_to_check += emb.description.lower()
                    if emb.title:
                        content_to_check += emb.title.lower()
            
            # Check for keywords
            for kw in bot_info["keywords"]:
                if kw in content_to_check:
                    last_bump_times[bot_info["name"]] = datetime.utcnow()
                    print(f"[BumpDetect] ✅ {bot_info['name']} bump confirmed!")
                    break
    
    await bot.process_commands(message)


@bot.event
async def on_ready():
    """Bot ready."""
    print(f'\n✅ {bot.user} is online!')
    
    # Check USER_TOKEN
    ut = get_user_token()
    if ut:
        masked = ut[:20] + "..." if len(ut) > 20 else ut
        print(f'🔑 USER_TOKEN set: {masked}')
    else:
        print(f'❌ USER_TOKEN NOT SET - Auto bump will fail!')
    
    # Set presence
    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="the server 🌙"
        )
    )
    
    # Cache invites
    for guild in bot.guilds:
        try:
            invites = await guild.fetch_invites()
            invite_cache[guild.id] = {inv.code: inv for inv in invites}
            print(f'📌 Cached {len(invites)} invites for: {guild.name}')
        except Exception as e:
            print(f'⚠️ Could not cache invites for {guild.name}: {e}')
    
    # Start auto bump task
    auto_bump_task.start()
    print('🔄 Auto bump task started (runs every 30 min)!\n')


@bot.event
async def on_invite_create(invite):
    """Track invite creation."""
    guild_id = invite.guild.id
    if guild_id not in invite_cache:
        invite_cache[guild_id] = {}
    invite_cache[guild_id][invite.code] = invite


@bot.event
async def on_invite_delete(invite):
    """Track invite deletion."""
    guild_id = invite.guild.id
    if guild_id in invite_cache and invite.code in invite_cache[guild_id]:
        del invite_cache[guild_id][invite.code]


@bot.event
async def on_member_join(member):
    """Track who invited the member."""
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
        print(f'⚠️ Invite tracking error: {e}')
    
    invite_channel_id = int(os.getenv('INVITE_CHANNEL_ID', 0))
    channel = guild.get_channel(invite_channel_id)
    
    if not channel:
        return
    
    if inviter:
        embed = discord.Embed(
            title="👋 New Member!",
            description=f"{member.mention} joined",
            color=0x5865F2
        )
        embed.add_field(name="Invited by", value=f"{inviter.mention}", inline=False)
        embed.add_field(name="Total Invites", value=f"{invite_count}", inline=False)
        await channel.send(embed=embed)
    else:
        await channel.send(f"{member.mention} joined (invite source unknown)")


# ──── COMMANDS ────

@bot.command(name='invites')
async def check_invites(ctx, member: discord.Member = None):
    """Check total invites by a member."""
    if member is None:
        member = ctx.author
    
    try:
        invites = await ctx.guild.fetch_invites()
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
    """Check auto bump status."""
    now = datetime.utcnow()
    lines = []
    
    available = guild_cmd_cache.get(ctx.guild.id, {})
    
    if not available:
        await ctx.send("⏳ Loading bump bots... Try again in a moment!")
        return
    
    for app_id, cmd_info in available.items():
        bot_info = BUMP_BOTS[app_id]
        name = bot_info["name"]
        cooldown_h = bot_info["cooldown_h"]
        last_t = last_bump_times.get(name)
        
        if last_t is None:
            lines.append(f'✅ **{name}** — Ready to bump! (cooldown: {cooldown_h}h)')
        else:
            remaining = timedelta(hours=cooldown_h) - (now - last_t)
            if remaining.total_seconds() <= 0:
                lines.append(f'✅ **{name}** — Ready to bump! (cooldown: {cooldown_h}h)')
            else:
                mins = int(remaining.total_seconds() // 60)
                secs = int(remaining.total_seconds() % 60)
                lines.append(f'⏳ **{name}** — {mins}m {secs}s remaining')
    
    embed = discord.Embed(
        title='🚀 Auto Bump Status',
        description='\n'.join(lines) if lines else "No bump bots available",
        color=0x5865F2,
        timestamp=now
    )
    embed.set_footer(text='Auto-bumps every 30 minutes')
    await ctx.send(embed=embed)


@bot.command(name='forcebump')
@commands.has_permissions(administrator=True)
async def force_bump(ctx):
    """Force run all bumps immediately."""
    embed = discord.Embed(
        title="⚡ Force Bump",
        description="Running all bumps now...",
        color=0xFAA61A
    )
    msg = await ctx.send(embed=embed)
    
    # Clear cooldowns
    last_bump_times.clear()
    
    # Refresh command cache
    guild_cmd_cache[ctx.guild.id] = await fetch_guild_bump_commands(ctx.guild)
    
    # Run bumps
    await run_all_bumps()
    
    embed = discord.Embed(
        title="✅ Force Bump Complete",
        description="All bumps have been triggered!",
        color=0x57F287
    )
    await msg.edit(embed=embed)


@bot.command(name='listbumpbots')
async def list_bump_bots(ctx):
    """List detected bump bots."""
    available = guild_cmd_cache.get(ctx.guild.id, {})
    
    if not available:
        available = await fetch_guild_bump_commands(ctx.guild)
        guild_cmd_cache[ctx.guild.id] = available
    
    if not available:
        embed = discord.Embed(
            title="❌ No Bump Bots",
            description="No supported bump bots found in this server.",
            color=0xED4245
        )
        await ctx.send(embed=embed)
        return
    
    lines = []
    for app_id, cmd_info in available.items():
        info = BUMP_BOTS[app_id]
        cooldown = info["cooldown_h"]
        lines.append(f'✅ **{info["name"]}** — cooldown: {cooldown}h')
    
    embed = discord.Embed(
        title='🤖 Detected Bump Bots',
        description='\n'.join(lines),
        color=0x57F287
    )
    await ctx.send(embed=embed)


@bot.command(name='refreshbumpbots')
@commands.has_permissions(administrator=True)
async def refresh_bump_bots(ctx):
    """Refresh and re-detect bump bots."""
    embed = discord.Embed(
        title="🔄 Refreshing Bump Bots",
        description="Please wait...",
        color=0x5865F2
    )
    msg = await ctx.send(embed=embed)
    
    # Clear cache for this guild
    if ctx.guild.id in guild_cmd_cache:
        del guild_cmd_cache[ctx.guild.id]
    
    # Fetch fresh
    available = await fetch_guild_bump_commands(ctx.guild)
    guild_cmd_cache[ctx.guild.id] = available
    
    if not available:
        embed = discord.Embed(
            title="❌ No Bump Bots Found",
            description="Could not detect any supported bump bots.",
            color=0xED4245
        )
    else:
        lines = []
        for app_id, cmd_info in available.items():
            info = BUMP_BOTS[app_id]
            lines.append(f'✅ {info["name"]}')
        
        embed = discord.Embed(
            title="✅ Bump Bots Refreshed",
            description=f"Found {len(available)} bot(s):\n" + '\n'.join(lines),
            color=0x57F287
        )
    
    await msg.edit(embed=embed)


# ──── HEALTH SERVER ────
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
    print(f"✅ Health server running on port {port}\n")


async def main():
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print('❌ ERROR: DISCORD_TOKEN not set!')
        return
    
    await run_health_server()
    await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
