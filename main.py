import discord
from discord.ext import commands, tasks
import os
import asyncio
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

BUMP_BOTS = {
    "Disboard": {
        "cmd": "/bump",
        "cooldown_h": 2,
        "keywords": ["bump done", "bumped", "server bumped"],
    },
    "Carl-bot": {
        "cmd": "/bump",
        "cooldown_h": 24,
        "keywords": ["bumped", "bump", "carl.gg"],
    },
    "Discadia": {
        "cmd": "/bump",
        "cooldown_h": 1,
        "keywords": ["bumped", "bump successful"],
    },
}


def get_bump_channel(guild):
    """Bump channel dhundho."""
    bump_channel_id = int(os.getenv('BUMP_CHANNEL_ID', 0))
    channel = guild.get_channel(bump_channel_id)
    
    if not channel:
        for ch in guild.text_channels:
            if 'bump' in ch.name.lower():
                return ch
    
    return channel


async def run_all_bumps():
    """Main auto bump engine - text commands use karo."""
    for guild in bot.guilds:
        print(f"\n[AutoBump] Processing: {guild.name}")
        
        channel = get_bump_channel(guild)
        if not channel:
            print(f"[AutoBump] ❌ No bump channel found")
            continue
        
        now = datetime.now(datetime.timezone.utc)
        
        # Disboard bump
        if now - last_bump_times.get("Disboard", datetime.min) >= timedelta(hours=2):
            print(f"[AutoBump] 🚀 Triggering Disboard...")
            try:
                await channel.send("/bump")
                last_bump_times["Disboard"] = now
                print(f"[AutoBump] ✅ Disboard command sent")
            except Exception as e:
                print(f"[AutoBump] ❌ Disboard error: {e}")
            await asyncio.sleep(3)
        else:
            remaining = timedelta(hours=2) - (now - last_bump_times.get("Disboard", datetime.min))
            mins = int(remaining.total_seconds() // 60)
            print(f"[AutoBump] ⏳ Disboard cooldown: {mins}m remaining")
        
        # Carl-bot bump
        if now - last_bump_times.get("Carl-bot", datetime.min) >= timedelta(hours=24):
            print(f"[AutoBump] 🚀 Triggering Carl-bot...")
            try:
                await channel.send("/bump")
                last_bump_times["Carl-bot"] = now
                print(f"[AutoBump] ✅ Carl-bot command sent")
            except Exception as e:
                print(f"[AutoBump] ❌ Carl-bot error: {e}")
            await asyncio.sleep(3)
        else:
            remaining = timedelta(hours=24) - (now - last_bump_times.get("Carl-bot", datetime.min))
            hours = int(remaining.total_seconds() // 3600)
            print(f"[AutoBump] ⏳ Carl-bot cooldown: {hours}h remaining")
        
        # Discadia bump
        if now - last_bump_times.get("Discadia", datetime.min) >= timedelta(hours=1):
            print(f"[AutoBump] 🚀 Triggering Discadia...")
            try:
                await channel.send("/bump")
                last_bump_times["Discadia"] = now
                print(f"[AutoBump] ✅ Discadia command sent")
            except Exception as e:
                print(f"[AutoBump] ❌ Discadia error: {e}")
            await asyncio.sleep(3)
        else:
            remaining = timedelta(hours=1) - (now - last_bump_times.get("Discadia", datetime.min))
            secs = int(remaining.total_seconds())
            print(f"[AutoBump] ⏳ Discadia cooldown: {secs}s remaining")


@tasks.loop(minutes=30)
async def auto_bump_task():
    """Every 30 minutes run bumps."""
    print(f"\n{'='*70}")
    print(f"[AutoBump] ⏰ Task tick at {datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*70}")
    await run_all_bumps()


@auto_bump_task.before_loop
async def before_auto_bump():
    """Setup before auto bump."""
    await bot.wait_until_ready()
    await asyncio.sleep(5)
    print("\n[AutoBump] 🔄 Initial setup...")
    await run_all_bumps()


@bot.event
async def on_message(message):
    """Detect bump confirmations."""
    if message.author == bot.user:
        return
    
    # Disboard detection
    if message.author.name == "Disboard":
        content = (message.content + " " + str(message.embeds)).lower()
        if any(kw in content for kw in ["bump done", "bumped", "server bumped"]):
            last_bump_times["Disboard"] = datetime.now(datetime.timezone.utc)
            print(f"[BumpDetect] ✅ Disboard bump confirmed!")
    
    # Carl-bot detection
    if message.author.name == "Carl-bot":
        content = (message.content + " " + str(message.embeds)).lower()
        if any(kw in content for kw in ["bumped", "bump", "carl.gg"]):
            last_bump_times["Carl-bot"] = datetime.now(datetime.timezone.utc)
            print(f"[BumpDetect] ✅ Carl-bot bump confirmed!")
    
    # Discadia detection
    if message.author.name == "Discadia":
        content = (message.content + " " + str(message.embeds)).lower()
        if any(kw in content for kw in ["bumped", "bump successful"]):
            last_bump_times["Discadia"] = datetime.now(datetime.timezone.utc)
            print(f"[BumpDetect] ✅ Discadia bump confirmed!")
    
    await bot.process_commands(message)


@bot.event
async def on_ready():
    """Bot ready."""
    print(f'\n✅ {bot.user} is online!')
    
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
    print('🔄 Auto bump task started (every 30 min)!\n')


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

@bot.command(name='bumpstatus')
async def bump_status(ctx):
    """Check auto bump status."""
    now = datetime.now(datetime.timezone.utc)
    lines = []
    
    # Disboard
    last_t = last_bump_times.get("Disboard")
    if last_t is None:
        lines.append(f'✅ **Disboard** — Ready! (cooldown: 2h)')
    else:
        remaining = timedelta(hours=2) - (now - last_t)
        if remaining.total_seconds() <= 0:
            lines.append(f'✅ **Disboard** — Ready! (cooldown: 2h)')
        else:
            mins = int(remaining.total_seconds() // 60)
            lines.append(f'⏳ **Disboard** — {mins}m remaining')
    
    # Carl-bot
    last_t = last_bump_times.get("Carl-bot")
    if last_t is None:
        lines.append(f'✅ **Carl-bot** — Ready! (cooldown: 24h)')
    else:
        remaining = timedelta(hours=24) - (now - last_t)
        if remaining.total_seconds() <= 0:
            lines.append(f'✅ **Carl-bot** — Ready! (cooldown: 24h)')
        else:
            hours = int(remaining.total_seconds() // 3600)
            lines.append(f'⏳ **Carl-bot** — {hours}h remaining')
    
    # Discadia
    last_t = last_bump_times.get("Discadia")
    if last_t is None:
        lines.append(f'✅ **Discadia** — Ready! (cooldown: 1h)')
    else:
        remaining = timedelta(hours=1) - (now - last_t)
        if remaining.total_seconds() <= 0:
            lines.append(f'✅ **Discadia** — Ready! (cooldown: 1h)')
        else:
            mins = int(remaining.total_seconds() // 60)
            lines.append(f'⏳ **Discadia** — {mins}m remaining')
    
    embed = discord.Embed(
        title='🚀 Auto Bump Status',
        description='\n'.join(lines),
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
