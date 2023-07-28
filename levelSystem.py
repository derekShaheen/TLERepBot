from configManager import load_guild_data, load_config, save_user_data, load_user_data, save_guild_data
import discord
import math
from functools import lru_cache
from os import path
import glob
import discord

import asciichartpy
import pandas as pd
from datetime import datetime

async def process_experience(ctx, guild, member, experience_addition, debug = False):

    user_data = load_user_data(guild.id, member.id)
    if user_data.get('blacklisted'):
        if debug:
            timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
            print(f"{timestamp}      Issued 0xp to {member.name} [blacklisted].")
        return 0
    
    # Current level
    current_level = user_data['level']

    # Don't issue experience if the member's status is idle
    if member.status == discord.Status.idle:
        if debug:
            timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
            print(f"{timestamp}      Issued 0xp to {member.name} [idle]. Experience: {(user_data['experience'] + experience_addition)}, Level: {current_level}")
        return

    # Add the experience to the user's total
    user_data['experience'] += experience_addition
    if user_data['experience'] < 0:
        user_data['experience'] = 0

    # Calculate new level
    new_level = calculate_level(user_data['experience'])
    user_data['level'] = new_level

    # Save user data
    save_user_data(guild.id, member.id, user_data)

    # Adjust roles
    await adjust_roles(guild, current_level, new_level, member)
    
    if debug:
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        print(f"{timestamp}      Issued {experience_addition}xp to {member.name}. Experience: {(user_data['experience'] + experience_addition)}, New Level: {new_level}, Prior Level: {current_level}")

    if current_level != new_level:
        await log_level_up(ctx, guild, member, new_level)

    return new_level

async def generate_leaderboard(bot, guild_id):
    user_data_files = glob.glob(f'data/{guild_id}/[!guild_data]*.yaml')

    user_data_list = []
    for user_data_file in user_data_files:
        user_id = path.splitext(path.basename(user_data_file))[0]
        user_data = load_user_data(guild_id, user_id)
        user_data_list.append((user_id, user_data))

    user_data_list.sort(key=lambda item: item[1]['experience'], reverse=True)

    leaderboard_data = []
    leaderboard_levels = []
    min_level = 9999
    max_level = 0
    max_username_len = 0
    rank_emoji = ["🥇", "🥈", "🥉"] + ["🏅"]*2 + ["🔹"]*2 + ["🔸"]*2 + [""]*10
    #for rank, (user_id, user_data) in enumerate(user_data_list[:10], start=1):
    for rank, (user_id, user_data) in enumerate(user_data_list[:10], start=1):
        user = await bot.fetch_user(int(user_id))
        username = user.display_name or user.name
        username = username[0].upper() + username[1:]  # Capitalize the first letter
        username = f'{rank_emoji[min(rank-1, len(rank_emoji)-1)]} {username}'
        max_username_len = max(max_username_len, len(username))  # Track the maximum username length
        leaderboard_data.append((username, user_data["level"], user_data["experience"]))
        leaderboard_levels.append(user_data['level'])
        min_level = min(min_level, user_data["level"])  # Track the minimum level
        max_level = max(max_level, user_data["level"])  # Track the maximum level
    # Duplicate each level 3 times to stretch the plot
    stretched_leaderboard_levels = [lvl for lvl in leaderboard_levels for _ in range(3)]
    stretched_leaderboard_levels.append(min_level)

    # Generate ASCII plot for levels
    ascii_plot = asciichartpy.plot(stretched_leaderboard_levels, {'format': '{:>6.0f}'})

    # Add label
    ascii_plot = ascii_plot + '\n\n\t\t\tTop 9 Users by Rank'

    # Add user labels to the plot, pad usernames to align level and XP info
    for username, level, xp in leaderboard_data[:9]:
        ascii_plot += '\n' + username.ljust(max_username_len) + f'  (Level: {level}, XP: {round(xp)})'

    # Add label
    ascii_plot = '   Level\n' + ascii_plot

    # Add title
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:00]")
    ascii_plot = '\n\t\t\t' + timestamp + '\n   Earn XP by participating in the server!\n' + ascii_plot

    # Return the ASCII plot
    return ascii_plot

# async def generate_leaderboard(bot, guild_id):
#     user_data_files = glob.glob(f'data/{guild_id}/[!guild_data]*.yaml')

#     user_data_list = []
#     for user_data_file in user_data_files:
#         user_id = path.splitext(path.basename(user_data_file))[0]
#         user_data = load_user_data(guild_id, user_id)
#         user_data_list.append((user_id, user_data))

#     user_data_list.sort(key=lambda item: item[1]['experience'], reverse=True)

#     leaderboard_data = []
#     max_level = 0
#     max_experience = 0
#     for rank, (user_id, user_data) in enumerate(user_data_list[:10], start=1):
#         user = await bot.fetch_user(int(user_id))
#         # Add the rank prefix to the username
#         leaderboard_data.append([f'{rank}. {user.name}', user_data["level"], user_data["experience"]])
#         max_level = max(max_level, user_data["level"])  # Track the maximum level
#         max_experience = max(max_experience, user_data["experience"])  # Track the maximum experience

#     # Convert the data into a Pandas DataFrame and sort by level
#     df = pd.DataFrame(leaderboard_data, columns=['User', 'Level', 'Experience'])
#     df.sort_values('Level', inplace=True)

#     # Create the plot
#     plt.figure(figsize=(10, 5))

#     # Get the cumulative experience for each level up to max_level and
#     # duplicate each value, shifting the levels by 0.99 for the second value
#     experiences = cumulative_experience_for_level()[:max_level+1]
#     levels = [i + j/100.0 for i in range(max_level+1) for j in [0, 99]]
#     experiences_step = [val for val in experiences for _ in (0, 1)]

#     # Plot the line for the experience per level
#     sns.lineplot(x=levels, y=experiences_step, color='blue')

#     # Plot the users on the leaderboard
#     palette = sns.color_palette("hsv", len(leaderboard_data))
#     scatter = sns.scatterplot(x='Level', y='Experience', hue='User', palette=palette, s=100, data=df)

#     # Sort the legend labels by the rank prefix
#     handles, labels = scatter.get_legend_handles_labels()
#     labels, handles = zip(*sorted(zip(labels, handles), key=lambda t: int(t[0].split('.')[0])))
#     scatter.legend(handles, labels)

#     plt.title('Leaderboard')
#     plt.xlabel('Level')
#     plt.ylabel('Experience')

#     # Set x and y limits
#     plt.xlim(0, max_level+1)
#     plt.ylim(0, max_experience+100)  # Adding a little padding to the maximum experience for aesthetics

#     # Save it to a BytesIO object
#     buf = io.BytesIO()
#     plt.savefig(buf, format='png')
#     buf.seek(0)

#     # Return the BytesIO object
#     return buf


#@lru_cache(maxsize=None)  # Unbounded cache, you may want to restrict the size in a real application
def calculate_level(experience, debug = False):
    # Get experience constant from config
    config = load_config()
    experience_constant = config['experience_constant']
    
    # Using the formula: level = (level * math.pow((level, experience_constant)) + 30)
    level = 1
    while experience >= (level * (math.pow(level, experience_constant)) + 30):
        if debug:
            # Print on one line
            print(f"Level: {level}, Experience: {experience}, Change: {(level * (math.pow(level, experience_constant)) + 30)}")
        experience -= (level * (math.pow(level, experience_constant)) + 30)
        level += 1
    
    return level

@lru_cache(maxsize=None)  # Unbounded cache, you may want to restrict the size in a real application
def cumulative_experience_for_level(debug=False):
    # Get experience constant from config
    config = load_config()
    experience_constant = config['experience_constant']
    
    # Set target level
    target_level = 200

    experience_list = [0]  # Start the list with 0 so that the indexes line up with the levels
    for level in range(1, target_level+1):
        experience_for_level = (level * (level ** experience_constant)) + 30
        total_experience = experience_list[-1] + experience_for_level
        experience_list.append(total_experience)
        if debug:
            print(f"Level: {level}, Experience: {total_experience}, Experience for level: {experience_for_level}")

    return experience_list


async def adjust_roles(guild, old_level, new_level, member):
    if new_level > old_level:
        await assign_roles_on_level_up(guild, new_level, member)
    elif new_level <= old_level:
        await unassign_roles_above_level(guild, new_level, member)

async def assign_roles_on_level_up(guild, new_level, member):
    guild_data = load_guild_data(guild.id)

    if 'level_roles' in guild_data:
        level_roles = guild_data['level_roles']
        level = new_level

        # Iterate through all level roles that are within the user's current level
        for l in range(1, level + 1):
            if str(l) in level_roles:
                role = discord.utils.get(guild.roles, id=level_roles[str(l)])
                
                if role and role not in member.roles:
                    await member.add_roles(role)

async def unassign_roles_above_level(guild, new_level, member):
    guild_data = load_guild_data(guild.id)

    if 'level_roles' in guild_data:
        level_roles = guild_data['level_roles']
        level = new_level

        # iterate through all level roles above the user's current level
        for l in range(level + 1, max(map(int, level_roles.keys())) + 1):
            if str(l) in level_roles:
                role = discord.utils.get(guild.roles, id=level_roles[str(l)])
                
                if role and role in member.roles:
                    await member.remove_roles(role)

async def log_level_up(ctx, guild, member, new_level):
    guild_data = load_guild_data(guild.id)
    levelup_log_channel_id = guild_data.get('publog')
    levelup_log_message_id = guild_data.get('levelup_log_message')
    levelup_log_channel = ctx.get_channel(levelup_log_channel_id) if levelup_log_channel_id else None
    levelup_log_message = None

    if levelup_log_channel and levelup_log_message_id:
        try:
            levelup_log_message = await levelup_log_channel.fetch_message(levelup_log_message_id)
        except discord.NotFound:
            levelup_log_message_id = None  # Reset the message ID if the message was not found

    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M]")
    member_name = member.name[0].upper() + member.name[1:]  # Capitalize member's name
    new_levelup_text = f"{member_name} is now level {new_level}!"

    # If the levelup_log exists in guild_data, append the new level up text to the list
    # and slice the list to keep only the last 10 elements. If it does not exist, initialize it
    guild_data.setdefault('levelup_log', [])
    guild_data['levelup_log'].append((timestamp, new_levelup_text))
    guild_data['levelup_log'] = guild_data['levelup_log'][-6:]
    save_guild_data(guild.id, guild_data)

    levelup_embed = discord.Embed(
        title="Level Up Log!",
        color=discord.Color.green()
    )

    for timestamp, log_text in guild_data['levelup_log']:
        levelup_embed.add_field(name=timestamp + ' ' + log_text, value='\u200b', inline=False)

    if levelup_log_message:  # If a message already exists, edit it
        await levelup_log_message.edit(embed=levelup_embed)
    else:  # If no message exists, send a new one and save its ID
        if levelup_log_channel:
            levelup_log_message = await levelup_log_channel.send(embed=levelup_embed)
            guild_data['levelup_log_message'] = levelup_log_message.id
            save_guild_data(guild.id, guild_data)
        else:
            print(f"Level up log channel not found for guild {guild.id} ({guild.name})")
