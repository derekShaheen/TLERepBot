from datetime import datetime, timedelta, time
import importlib
import subprocess
import sys

libraries = [
    ("discord", "discord.py"),
    ("asyncio", "asyncio"),
    ("datetime", "datetime"),
    # ("gnuplotlib", "gnuplotlib"),
    # ("pandas"),
]

for library in libraries:
    try:
        importlib.import_module(library[0])
    except ImportError:
        print(f"{library[0]} not installed. Installing...")
        subprocess.call([sys.executable, "-m", "pip", "install", library[1]])

import asyncio
import discord
from discord.ext import commands, tasks

import _secrets
from commandsAdmin import set_level, xp, set_level_role, set_channel, toggle_blacklist
from commandsUser import level#, leaderboard
from configManager import load_user_data, load_config, save_user_data, load_guild_data, save_guild_data
from levelSystem import process_experience, generate_leaderboard
from util import send_embed, get_initial_delay

debug = True

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents, reconnect=True)
config = load_config()

bot.add_command(set_level)
bot.add_command(set_level_role)
bot.add_command(xp)
bot.add_command(level)
#bot.add_command(leaderboard)
bot.add_command(set_channel)
bot.add_command(toggle_blacklist)

@bot.event
async def on_ready():
    voice_activity_tracker.start()
    update_leaderboard.start()
#    await update_leaderboard()

@tasks.loop(minutes=1)
async def voice_activity_tracker():
    if debug:
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        print(f"{timestamp} Updating credits...")
    config = load_config()
    for guild in bot.guilds:
        for member in guild.members:
            # Check if the member is connected to a voice channel (but not the AFK channel)
            if member.voice and member.voice.channel and (member.voice.channel.id != guild.afk_channel):
                # Check if the member is alone in the voice channel
                is_alone = len(member.voice.channel.members) == 1
                # Check if all other members are idle
                all_others_idle = all(other_member.status == discord.Status.idle for other_member in member.voice.channel.members if other_member != member)

                # Calculate the experience gain based on whether the member is alone, with others or with idle members only
                if is_alone:
                    experience_gain = config['experience_per_minute_voice'] / 4
                elif all_others_idle:
                    experience_gain = config['experience_per_minute_voice'] / 4
                else:
                    experience_gain = config['experience_per_minute_voice']

                # Add experience and level up if necessary
                await process_experience(bot, guild, member, experience_gain, True)
    if debug:
        print(f"{timestamp} ...credit update complete.")


@voice_activity_tracker.before_loop
async def before_voice_activity_tracker():
    initial_delay = get_initial_delay(interval=timedelta(minutes=1))
    if debug:
        print('Update credits scheduled for: {}'.format(initial_delay))
    await asyncio.sleep(initial_delay)

@bot.event
async def on_message(message):
    # Avoid responding to bot messages
    if message.author.bot:
        return

    if message.content.startswith('!'):
        await bot.process_commands(message)
        return

    config = load_config()

    # Load or initialize user data
    user_data = load_user_data(message.guild.id, message.author.id)

    now = datetime.now()

    # Initialize 'chats_timestamps' if it doesn't exist
    if 'chats_timestamps' not in user_data:
        user_data['chats_timestamps'] = []

    # Remove timestamps older than 1 minute
    user_data['chats_timestamps'] = [timestamp for timestamp in user_data['chats_timestamps'] if now - timestamp < timedelta(minutes=1)]
    
    # Check for spamming (10 points per minute)
    user_data['chats_timestamps'].append(now)
    if len(user_data['chats_timestamps']) >= config['spam_limit']:
        if debug:
            print(f"Blocked points for spamming: {len(user_data['chats_timestamps'])} / {config['spam_limit']}")
        return  # Don't award points or send a level-up message

    # Save user data after updating it
    save_user_data(message.guild.id, message.author.id, user_data)

    # Check if the user is connected to a voice channel
    experience_per_chat = config['experience_per_chat']
    if message.author.voice and message.author.voice.channel:
        # If the user is in a voice channel, penalize the experience
        experience_per_chat /= 2

    # Process commands after checking for spam and awarding points
    await bot.process_commands(message)

@tasks.loop(minutes=60)
async def update_leaderboard():
    if debug:
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        print(f"{timestamp} Updating leaderboard...", end='', flush=True)

    for guild in bot.guilds:
        guild_data = load_guild_data(guild.id)
        leaderboard_channel_id = guild_data.get('leaderboard')
        leaderboard_channel = bot.get_channel(leaderboard_channel_id) if leaderboard_channel_id else None

        if leaderboard_channel:
            ascii_plot = await generate_leaderboard(bot, guild.id)

            leaderboard_message_id = guild_data.get('leaderboard_message')
            leaderboard_message = None

            # Try to fetch the message, but handle the error if it doesn't exist
            if leaderboard_message_id:
                try:
                    leaderboard_message = await leaderboard_channel.fetch_message(leaderboard_message_id)
                except discord.errors.NotFound:
                    leaderboard_message = None  # Reset to None if the message was not found
                    
            lb_embed = discord.Embed(
                title="Leaderboard for The Last Echelon",
                description=f"```{ascii_plot}```",
                color=discord.Color.gold()
            )

            if leaderboard_message:
                #await leaderboard_message.edit(content='', embed=discord.Embed(description=f"```{ascii_plot}```"))  # Edit the old message
                await leaderboard_message.edit(embed=lb_embed)  # Edit the old message
            else:
                leaderboard_message = await leaderboard_channel.send(embed=lb_embed)  # Send a new message
                #leaderboard_message = await send_embed(leaderboard_channel, title="Leaderboard", description=f"```{ascii_plot}```", color=0x00ff00)

            guild_data['leaderboard_message'] = leaderboard_message.id
            save_guild_data(guild.id, guild_data)
    if debug:
        print("Update complete.")

@update_leaderboard.before_loop
async def before_update_leaderboard():
    initial_delay = get_initial_delay(interval=timedelta(hours=1, seconds=5))
    if debug:
        print('Update leaderboard scheduled for: {}'.format(initial_delay))
    await asyncio.sleep(initial_delay)

# @tasks.loop(minutes=60)
# async def update_leaderboard():
#     for guild in bot.guilds:
#         guild_data = load_guild_data(guild.id)
#         leaderboard_channel_id = guild_data.get('leaderboard')
#         leaderboard_channel = bot.get_channel(leaderboard_channel_id) if leaderboard_channel_id else None

#         if leaderboard_channel:
#             image = await generate_leaderboard(bot, guild.id)
#             file = discord.File(image, filename="leaderboard.png")
#             leaderboard_message_id = guild_data.get('leaderboard_message')
#             leaderboard_message = None

#             # Try to fetch the message, but handle the error if it doesn't exist
#             if leaderboard_message_id:
#                 try:
#                     leaderboard_message = await leaderboard_channel.fetch_message(leaderboard_message_id)
#                 except discord.errors.NotFound:
#                     leaderboard_message = None  # Reset to None if the message was not found

#             if leaderboard_message:
#                 await leaderboard_message.delete()  # Delete the old message
#             leaderboard_message = await leaderboard_channel.send(file=file)  # Send a new message
#             guild_data['leaderboard_message'] = leaderboard_message.id
#             save_guild_data(guild.id, guild_data)

async def run_bot():
    while True:
        try:
            await bot.start(_secrets.DISCORD_TOKEN)  # Replace TOKEN with your bot token
        except (discord.ConnectionClosed, discord.GatewayNotFound, discord.HTTPException) as exc:
            print(f"Connection error occurred: {exc}, trying to reconnect...")

            # Wait for bot to be ready with a timeout
            try:
                await asyncio.wait_for(bot.wait_until_ready(), timeout=60)
            except asyncio.TimeoutError:
                print("Reconnect failed, restarting the bot...")
                await bot.close()
        except discord.errors.LoginFailure:
            print(
                "An improper token was provided. Please check your token and try again.")
            await bot.close()
        except KeyboardInterrupt:
            await bot.close()
            break
        except Exception as exc:
            print(f"An unexpected error occurred: {exc}")
            await bot.close()
            break

if __name__ == "__main__":
    asyncio.run(run_bot())
