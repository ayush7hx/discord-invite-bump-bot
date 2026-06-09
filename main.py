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
        "cooldown_h": 2,
        "keywords": ["bump done", "bumped", "server bumped"],
        "bot_int_id": 302050872383242240,
    },
    "235148962103951360": {
        "name": "Carl-bot",
        "cmd_name": "bump",
        "cooldown_h": 24,
        "keywords": ["bumped", "bump", "carl.gg"],
        "bot_int_id": 235148962103951360,
    },
    "1222548162741084311": {
        "name": "Discadia",
        "cmd_name": "bump",
        "cooldown_h": 1,
        "keywords": ["bumped", "bump successful"],
        "bot_int_id": 1222548162741084311,
    },
}

guild_cmd_cache = {}


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


async def fetch_guild_bump_commands(guild: discord.Guild):
    """Guild mein available bump bots detect karo."""
    found = {}
    
    for app_id, bot_info in BUMP_BOTS.items():
        member = guild.get_member(bot_info["bot_int_id"])
        if member is not None:
            found[app_id] = {
                "cmd_name": bot_info["cmd_name"],
                "bot_name": bot_info["name"],
            }
            print(f"[BotDetect] ✅ {bot_info['name']} found in '{guild.name}'")
        else:
            print(f"[BotDetect] ❌ {bot_info['name']} not in '{guild.name}'")
    
    return found


async def trigger_slash_bump(guild: discord.Guild, channel: discord.TextChannel,
                             app_id: str, bot_name: str, cmd_name: str) -> bool:
    """Slash command trigger karo."""
    user_token = get_user_token()
    if not user_token:
        print(f"[SlashBump] ❌ USER_TOKEN not set!")
        return False
    
    # API v10 ke saath simple interaction
    url = "https://discord.com/api/v10/interactions"
    
    payload = {
        "type": 2,
        "application_id": app_id,
        "guild_id": str(guild.id),
        "channel_id": str(channel.id),
        "session_id": make_session_id(),
        "data": {
            "type": 1,
            "name": cmd_name,
            "options": []
        },
        "nonce": make_nonce()
    }
    
    headers = get_browser_headers(user_token)
    
    print(f"[SlashBump] 🔄 Attempting {bot_name}... ")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                status = resp.status
                text = await resp.text()
                
                print(f"[SlashBump] Response: HTTP {status}")
                
                if status in (200, 204):
                    print(f"[SlashBump] ✅ {bot_name} success!")
                    return True
                elif status == 401:
                    print(f"[SlashBump] ❌ 401 Unauthorized - Invalid USER_TOKEN!")
                    print(f"[SlashBump] Response: {text[:300]}")
                    return False
                elif status == 403:
                    print(f"[SlashBump] ❌ 403 Forbidden - No permissions!")
                    return False
                elif status == 404:
                    print(f"[SlashBump] ❌ 404 Not Found - Invalid channel/guild!")
                    return False
                else:
                    print(f"[SlashBump] ⚠️ {bot_name} failed: {text[:300]}")
                    return False
    except asyncio.TimeoutError:
        print(f"[SlashBump] ⏱️ Timeout: {bot_name}")
        return False
    except Exception as e:
        print(f"[SlashBump] ❌ Exception: {str(e)}")
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
        print(f"\n[AutoBump] Processing guild: {guild.name}")
        
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
            print(f"[AutoBump] 🔄 Detecting bump bots for {guild.name}...")
            guild_cmd_cache[guild.id] = await fetch_guild_bump_commands(guild)
        
        available_cmds = guild_cmd_cache[guild.id]
        
        if not available_cmds:
            print(f"[AutoBump] ⚠️ No bump bots found in '{guild.name}'")
            continue
        
        print(f"[AutoBump] 📊 Found {len(available_cmds)} bot(s)")
        
        # Saare bump bots run karo
        for app_id, cmd_info in available_cmds.items():
            bot_name = cmd_info["bot_name"]
            cmd_name = cmd_info["cmd_name"]
            cooldown_h = BUMP_BOTS[app_id]["cooldown_h"]
            
            last_t = last_bump_times.get(bot_name)
            cooldown_ok = (last_t is None or now - last_t >= timedelta(hours=cooldown_h))
            
            if cooldown_ok:
                print(f"[AutoBump] 🚀 Running {bot_name}...")
                success = await trigger_slash_bump(guild, channel, app_id, bot_name, cmd_name)
                
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
                await asyncio.sleep(2)


@tasks.loop(minutes=30)
async def auto_bump_task():
    """Every 30 minutes auto bump."""
    print(f"\n{'='*60}")
    print(f"[AutoBump] ⏰ Task tick at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*60}")
    await run_all_bumps()


@auto_bump_task.before_loop
async def before_auto_bump():
    """Setup before auto bump."""
    await bot.wait_until_ready()
    await asyncio.sleep(5)
    print("\n[AutoBump] 🔄 Initial setup...")
    for guild in bot.guilds:
        guild_cmd_cache[guild.id] = await fetch_guild_bump_commands(guild)
    await run_all_bumps()


@bot.event
async def on_message(message):
    """Detect bump bot confirmations."""
    if message.author == bot.user:
        return
    
    for app_id, bot_info in BUMP_BOTS.items():
        if message.author.id == bot_info["bot_int_id"]:
            content_to_check = message.content.lower()
            
            if message.embeds:
                for emb in message.embeds:
                    if emb.description:
                        content_to_check += emb.description.lower()
                    if emb.title:
                        content_to_check += emb.title.lower()
            
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
    
    ut = get_user_token()
    if ut:
        masked = ut[:15] + "..." if len(ut) > 15 else ut
        print(f'🔑 USER_TOKEN: {masked}')
    else:
        print(f'❌ USER_TOKEN NOT SET!')
    
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
            print(f'📌 Cached {len(invites)} invites for: {guild.name}')
        except Exception as e:
            print(f'⚠️ Could not cache invites for {guild.name}: {e}')
    
    auto_bump_task.start()
    print('🔄 Auto bump task started!\n')


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
        bot_name = cmd_info["bot_name"]
        cooldown_h = BUMP_BOTS[app_id]["cooldown_h"]
        last_t = last_bump_times.get(bot_name)
        
        if last_t is None:
            lines.append(f'✅ **{bot_name}** — Ready! (cooldown: {cooldown_h}h)')
        else:
            remaining = timedelta(hours=cooldown_h) - (now - last_t)
            if remaining.total_seconds() <= 0:
                lines.append(f'✅ **{bot_name}** — Ready! (cooldown: {cooldown_h}h)')
            else:
                mins = int(remaining.total_seconds() // 60)
                lines.append(f'⏳ **{bot_name}** — {mins}m remaining')
    
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
        bot_name = cmd_info["bot_name"]
        cooldown = BUMP_BOTS[app_id]["cooldown_h"]
        lines.append(f'✅ **{bot_name}** — cooldown: {cooldown}h')
    
    embed = discord.Embed(
        title='🤖 Detected Bump Bots',
        description='\n'.join(lines),
        color=0x57F287
    )
    await ctx.send(embed=embed)


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
