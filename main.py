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

bump_channel_id = None
last_bump_time = None
bump_reminded = False

DISBOARD_ID = 302050872383242240


@bot.event
async def on_ready():
    print(f'✅ {bot.user} is now online!')
    for guild in bot.guilds:
        try:
            invites = await guild.fetch_invites()
            invite_cache[guild.id] = {inv.code: inv for inv in invites}
            print(f'Cached {len(invites)} invites for guild: {guild.name}')
        except Exception as e:
            print(f'Could not fetch invites for {guild.name}: {e}')
    bump_reminder_task.start()


@bot.event
async def on_invite_create(invite):
    guild_id = invite.guild.id
    if guild_id not in invite_cache:
        invite_cache[guild_id] = {}
    invite_cache[guild_id][invite.code] = invite
    print(f'New invite created: {invite.code} in {invite.guild.name}')


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
        print(f'Error on member join invite tracking: {e}')

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


@bot.event
async def on_message(message):
    global last_bump_time, bump_channel_id, bump_reminded

    if message.author.id == DISBOARD_ID:
        if message.embeds:
            for embed in message.embeds:
                desc = (embed.description or '').lower()
                if 'bump done' in desc or 'bumped' in desc:
                    last_bump_time = datetime.utcnow()
                    bump_channel_id = message.channel.id
                    bump_reminded = False
                    print(f'✅ Bump detected at {last_bump_time} in channel {bump_channel_id}')

    await bot.process_commands(message)


@tasks.loop(minutes=1)
async def bump_reminder_task():
    global last_bump_time, bump_reminded

    if last_bump_time is None:
        return

    now = datetime.utcnow()
    elapsed = now - last_bump_time

    if elapsed >= timedelta(hours=2) and not bump_reminded:
        channel_id = bump_channel_id or int(os.getenv('BUMP_CHANNEL_ID', 0))
        bump_role_id = os.getenv('BUMP_ROLE_ID', '')

        for guild in bot.guilds:
            channel = guild.get_channel(channel_id)
            if channel:
                mention = f'<@&{bump_role_id}>' if bump_role_id else '@everyone'

                embed = discord.Embed(
                    title='⏰ Time to Bump!',
                    description=(
                        f'{mention}\n\n'
                        f'It\'s been **2 hours** since the last bump!\n'
                        f'Use `/bump` to bump the server on **Disboard** and grow our community! 🚀'
                    ),
                    color=0x5865F2,
                    timestamp=now
                )
                embed.set_footer(text='Auto Bump Reminder • Every 2 Hours')

                await channel.send(embed=embed)
                bump_reminded = True
                print(f'📢 Bump reminder sent to channel {channel_id}')
                break


@bump_reminder_task.before_loop
async def before_bump_task():
    await bot.wait_until_ready()


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
        await ctx.send(f'❌ Could not fetch invites: {e}')


@bot.command(name='bumptimer')
async def bump_timer(ctx):
    if last_bump_time is None:
        await ctx.send('❌ No bump has been detected yet. Please bump first using `/bump`.')
        return

    now = datetime.utcnow()
    elapsed = now - last_bump_time
    remaining = timedelta(hours=2) - elapsed

    if remaining.total_seconds() <= 0:
        await ctx.send('✅ You can bump now! Use `/bump`')
    else:
        minutes = int(remaining.total_seconds() // 60)
        seconds = int(remaining.total_seconds() % 60)
        await ctx.send(f'⏳ Next bump available in **{minutes}m {seconds}s**')


token = os.getenv('DISCORD_TOKEN')
if not token:
    print('❌ ERROR: DISCORD_TOKEN not set in .env file!')
else:
    bot.run(token)
