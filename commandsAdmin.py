from discord.ext import commands
import discord
from configManager import load_guild_data, save_guild_data, load_user_data, save_user_data
from levelSystem import calculate_level, adjust_roles, cumulative_experience_for_level
from util import send_embed
from discord import Interaction
from discord import app_commands
from __main__ import bot

@bot.tree.command(description='Admin only command. Set the level of a specific user.')
@app_commands.guild_only()
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(member='The member whose level you want to set.')
@app_commands.describe(level='The level to set for the member.')
async def set_level(interaction: Interaction, member: discord.Member, level: int):
    # Load user data
    user_data = load_user_data(interaction.guild.id, member.id)
    
    # Save old level
    old_level = user_data['level']
    
    # Calculate the experience needed for the target level
    experience_list = cumulative_experience_for_level(level)
    experience = experience_list[-1]  # Get the last item from the list, which corresponds to the cumulative experience needed for the target level
    
    # Set the user's level and experience
    user_data['level'] = level
    user_data['experience'] = experience
    
    # Save user data
    save_user_data(interaction.guild.id, member.id, user_data)

    # Adjust roles
    await adjust_roles(interaction.guild, old_level, level, member)
    
    await interaction.response.send_message(f"{member.name}'s level has been set to {level}.")


@bot.tree.command(description='Admin only command. Adjust the experience of a specific user.')
@app_commands.guild_only()
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(member='The member whose experience you want to adjust.')
@app_commands.describe(experience='The experience to adjust for the member.')
async def setrep(interaction: Interaction, member: discord.Member, experience: int):
    # Load user data
    user_data = load_user_data(interaction.guild.id, member.id)
    
    # Old level
    old_level = user_data['level']
    
    # Adjust the experience in the user's total
    user_data['experience'] += experience
    if user_data['experience'] < 0:
        user_data['experience'] = 0

    # Calculate new level
    new_level = calculate_level(user_data['experience'])
    user_data['level'] = new_level

    # Save user data
    save_user_data(interaction.guild.id, member.id, user_data)

    # Adjust roles
    await adjust_roles(interaction.guild, old_level, new_level, member)
    
    # Send an embed message for leveling up or down
    embed = discord.Embed(
        title=f"{member.name}, your level has changed!", 
        description=f"You are now level {new_level}!", 
        color=0x00ff00 if new_level >= old_level else 0xff0000
    )
    await interaction.response.send_message(embed=embed)
    
    await interaction.response.send_message(f"{abs(experience)} experience points have been {'added to' if experience >= 0 else 'removed from'} {member.name}'s total.")

@bot.tree.command(description='Admin only command. Set a role for a specific level.')
@app_commands.guild_only()
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(level='The level you want to set the role for.')
@app_commands.describe(role='The role you want to set for the level.')
async def set_level_role(interaction: Interaction, level: int, role: discord.Role):
    # Load guild data
    guild_data = load_guild_data(interaction.guild.id)
    
    # Add the level-role mapping
    if 'level_roles' not in guild_data:
        guild_data['level_roles'] = {}
    guild_data['level_roles'][str(level)] = role.id
    
    # Save guild data
    save_guild_data(interaction.guild.id, guild_data)
    
    await interaction.response.send_message(f"The role for level {level} has been set to {role.name}.")

@bot.tree.command(description='Admin only command. Set a specific channel for certain notifications.')
@app_commands.guild_only()
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(channel_type='The type of the channel to set.')
@app_commands.describe(channel_name='The name of the channel to set for the type.')
async def set_channel(interaction: Interaction, channel_type: str, channel_name: str):
    guild_id = interaction.guild.id
    guild_data = load_guild_data(guild_id)
    
    if channel_type.lower() not in ['leaderboard', 'publog']:
        await interaction.response.send_message('Invalid channel type. Please specify either "leaderboard" or "publog".')
        return

    # Get the channel by its name
    channel = discord.utils.get(interaction.guild.channels, name=channel_name)
    if not channel:
        await interaction.response.send_message(f"Couldn't find a channel named {channel_name}.")
        return

    # Update the guild data
    guild_data[channel_type.lower()] = channel.id
    save_guild_data(guild_id, guild_data)

    await interaction.response.send_message(f"Set the {channel_type} channel to {channel_name}.")


@bot.tree.command(description='Admin only command. Toggle blacklist status for a user.')
@app_commands.guild_only()
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(user='The user to toggle blacklist status for.')
async def blacklist(interaction: Interaction, user: discord.Member):
    user_data = load_user_data(interaction.guild.id, user.id)
    # Toggle the blacklist status
    user_data['blacklisted'] = not user_data.get('blacklisted', False)
    save_user_data(interaction.guild.id, user.id, user_data)
    # Reply with the new status
    if user_data['blacklisted']:
        await interaction.response.send_message(f"{user.name} has been added to the blacklist.")
    else:
        await interaction.response.send_message(f"{user.name} has been removed from the blacklist.")
