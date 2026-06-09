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

# ─────────────────────────────────────────────
#  BUMP CONFIG
# ─────────────────────────────────────────────

# Disboard Bot App ID (fixed, never changes)
DISBOARD_APP_ID = "302050872383242240"
# Known Disboard /bump command ID (global slash command ID)
DISBOARD_CMD_ID = "947088344167366698"

# Per-bot cooldown tracker: { "bot_name": last_bumped_datetime }
last_bump_times = {}

# Bump bots detection (bot_id -> bump confirmation keywords in their embed)
BUMP_BOT_DETECTORS = {
    302050872383242240: {  # Disboard
        "name": "Disboard",
        "keywords": ["bump done", "bumped", "server bumped"],
        "cooldown_hours": 2,
    },
    1222548162741084311: {  # Discadia
        "name": "Discadia",
        "keywords": ["your server is bumped", "bump successful", "bumped"],
        "cooldown_hours": 1,
    },
    387774921943678977: {  # Discord.bots.gg
        "name": "Discord.bots.gg",
        "keywords": ["bump", "listed"],
        "cooldown_hours": 6,
    },
}


def make_nonce():
    ts = int(time.time() * 1000)
    return str((ts << 22) + random.randint(0, 4194303))


def make_session_id():
    return ''.join(random.choices(string.hexdigits.lower(), k=32))


# ─────────────────────────────────────────────
#  AUTO BUMP ENGINE
# ─────────────────────────────────────────────

async def do_disboard_bump(guild: discord.Guild, channel: discord.TextChannel):
    """
    Triggers Disboard /bump via Discord's interactions HTTP endpoint.
    Works by simulating a slash command interaction from the bot.
    """
    token = os.getenv('DISCORD_TOKEN')
    url = "https://discord.com/api/v10/interactions"

    payload = {
        "type": 2,
        "application_id": DISBOARD_APP_ID,
        "guild_id": str(guild.id),
        "channel_id": str(channel.id),
        "session_id": make_session_id(),
        "data": {
            "version": DISBOARD_CMD_ID,
            "id": DISBOARD_CMD_ID,
            "name": "bump",
            "type": 1,
            "options": [],
            "application_command": {
                "id": DISBOARD_CMD_ID,
                "application_id": DISBOARD_APP_ID,
                "version": DISBOARD_CMD_ID,
                "default_member_permissions": "0",
                "type": 1,
                "nsfw": False,
                "name": "bump",
                "description": "Bump your server!",
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
            print(f"[Disboard Bump] Status: {status} | Response: {text[:100]}")
            return status in (200, 204)


async def do_text_bump(channel: discord.TextChannel, command: str):
    """Send a text-based bump command (for prefix-command bump bots)."""
    try:
        await channel.send(command)
        print(f"[Text Bump] Sent '{command}' to #{channel.name}")
        return True
    except Exception as e:
        print(f"[Text Bump] Error sending '{command}': {e}")
        return False


async def run_all_bumps():
    """Run all configured bump commands across all guilds."""
    bump_channel_id = int(os.getenv('BUMP_CHANNEL_ID', 0))
    text_commands_raw = os.getenv('BUMP_TEXT_COMMANDS', '')
    text_commands = [c.strip() for c in text_commands_raw.split(',') if c.strip()]
    disboard_enabled = os.getenv('DISBOARD_AUTO_BUMP', 'true').lower() == 'true'

    for guild in bot.guilds:
        channel = guild.get_channel(bump_channel_id)
        if not channel:
            # Try to find a channel named bump/bumping
            for ch in guild.text_channels:
                if 'bump' in ch.name.lower():
                    channel = ch
                    break

        if not channel:
            print(f"[AutoBump] No bump channel found in {guild.name}, skipping.")
            continue

        now = datetime.utcnow()

        # ── Disboard /bump ──────────────────────────────
        if disboard_enabled:
            disboard_last = last_bump_times.get('Disboard')
            cooldown_ok = (
                disboard_last is None or
                now - disboard_last >= timedelta(hours=2)
            )
            if cooldown_ok:
                print(f"[AutoBump] Triggering Disboard /bump in {guild.name}...")
                success = await do_disboard_bump(guild, channel)
                if success:
                    last_bump_times['Disboard'] = now
                    embed = discord.Embed(
                        description='🚀 **Auto Bump triggered!** Bumped on Disboard!',
                        color=0x5865F2,
                        timestamp=now
                    )
                    await channel.send(embed=embed)
                else:
                    await channel.send('⚠️ Disboard auto-bump failed. Try `/bump` manually.')
            else:
                remaining = timedelta(hours=2) - (now - disboard_last)
                mins = int(remaining.total_seconds() // 60)
                print(f"[AutoBump] Disboard cooldown: {mins}m remaining.")

        # ── Text-based bump commands ─────────────────────
        for cmd in text_commands:
            cmd_key = f"text_{cmd}"
            last_t = last_bump_times.get(cmd_key)
            if last_t is None or now - last_t >= timedelta(hours=2):
                print(f"[AutoBump] Sending text command: {cmd}")
                success = await do_text_bump(channel, cmd)
                if success:
                    last_bump_times[cmd_key] = now
                await asyncio.sleep(3)  # Small delay between commands


# ─────────────────────────────────────────────
#  SCHEDULED TASK: runs every 30 min, checks cooldowns
# ─────────────────────────────────────────────

@tasks.loop(minutes=30)
async def auto_bump_task():
    print(f"[AutoBump] Checking bump cooldowns at {datetime.utcnow()}")
    await run_all_bumps()


@auto_bump_task.before_loop
async def before_auto_bump():
    await bot.wait_until_ready()
    # Run immediately on startup too
    await asyncio.sleep(5)
    await run_all_bumps()


# ─────────────────────────────────────────────
#  BUMP DETECTION (track when bump bots confirm)
# ─────────────────────────────────────────────

@bot.event
async def on_message(message):
    detector = BUMP_BOT_DETECTORS.get(message.author.id)
    if detector:
        content_to_check = ''
        if message.embeds:
            for emb in message.embeds:
                content_to_check += (emb.description or '') + (emb.title or '')
        content_to_check += message.content
        content_to_check = content_to_check.lower()

        for kw in detector['keywords']:
            if kw in content_to_check:
                last_bump_times[detector['name']] = datetime.utcnow()
                print(f"[BumpDetect] {detector['name']} bump confirmed!")
                break

    await bot.process_commands(message)


# ─────────────────────────────────────────────
#  INVITE TRACKER
# ─────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f'✅ {bot.user} is now online!')

    # Set bot status to Idle (moon 🌙)
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
        print(f'INVITE_CHANNEL_ID not set or channel not found!')
        return

    embed = discord.Embed(color=0x2b2d31, timestamp=datetime.utcnow())
    embed.set_author(
        name=f'{member.name} joined the server!',
        icon_url=member.display_avatar.url
    )

    if inviter:
        embed.description = (
            f'👋 {member.mention} has joined **{guild.name}**\n'
            f'📨 Invited by **{inviter.mention}** (`{inviter}`)\n'
            f'🎯 They now have **{invite_count}** invite(s) total'
        )
    else:
        embed.description = (
            f'👋 {member.mention} has joined **{guild.name}**\n'
            f'📨 Invite link could not be determined'
        )

    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f'Member #{guild.member_count}')
    await channel.send(embed=embed)


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
    for name, last_t in last_bump_times.items():
        elapsed = now - last_t
        remaining = timedelta(hours=2) - elapsed
        if remaining.total_seconds() <= 0:
            lines.append(f'✅ **{name}** — Ready to bump!')
        else:
            mins = int(remaining.total_seconds() // 60)
            lines.append(f'⏳ **{name}** — {mins}m remaining')

    if not lines:
        lines = ['No bumps detected yet. Bot will auto-bump shortly!']

    embed = discord.Embed(
        title='🚀 Auto Bump Status',
        description='\n'.join(lines),
        color=0x5865F2,
        timestamp=now
    )
    await ctx.send(embed=embed)


@bot.command(name='forcebump')
@commands.has_permissions(administrator=True)
async def force_bump(ctx):
    await ctx.send('⚡ Force running all bumps now...')
    # Reset timers so cooldown check passes
    last_bump_times.clear()
    await run_all_bumps()
    await ctx.send('✅ Done!')


token = os.getenv('DISCORD_TOKEN')
if not token:
    print('❌ ERROR: DISCORD_TOKEN not set in .env file!')
else:
    bot.run(token)
