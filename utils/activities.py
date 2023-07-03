import os
import aiohttp
import discord
from .constants import activity_index
from dotenv import load_dotenv
from pathlib import Path

# Auth
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
env_file_path = parent_dir / ".env"
load_dotenv(dotenv_path=env_file_path)

discordToken = os.getenv("DISCORD_TOKEN")


async def create_activity_invite(activity, channel_id: int):
    application_id = activity_index[activity]['id']
    headers = {
        'authorization': f'Bot {discordToken}',
        'content-type': 'application/json'
    }
    body = {
        'max_age': 0,
        'target_type': 2,# 2 == InviteTargetType.EmbeddedApplication
        'target_application_id': application_id
    }

    url = f'https://discord.com/api/v9/channels/{channel_id}/invites'

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=body) as resp:
            if resp.status == 200:
                invite = await resp.json()
                print(f'Invite created: https://discord.gg/{invite["code"]}')
                return invite["code"]
            else:
                e = await resp.json()
                print(f'Error: {e}')


async def get_activity_channel(
    interaction,
    activity,
    title: str = '',
    count: int = 0
):

    # guild_events = await interaction.guild.fetch_scheduled_events()
    if count == 0 and title == '':
        tmp_title = activity
    elif title == '':
        tmp_title = activity + f"-{count}"
    elif count == 0:
        tmp_title = title
    else:
        tmp_title = title + f"-{count}"

    act_cat = discord.utils.get(interaction.guild.channels, name='social')
    act_channel = discord.utils.get(interaction.guild.channels, name=tmp_title)

    if act_channel is None:
        print("Making play channel.")
        act_channel = await interaction.guild.create_voice_channel(name=tmp_title, category=act_cat)
        print(f"Made {act_channel}")
    elif len(act_channel.members) < activity_index[activity]['max'] or activity_index[activity]['max'] == 0:
        print("Play channel already exists!")
        pass
    elif len(act_channel.members) > activity_index[activity]['max']:
        print("Expanding play channels!")
        # play_channel = await interaction.guild.create_voice_channel(name=f'{title}-2', category=play_cat)
        act_channel = await get_activity_channel(interaction, activity, title, count+1)

    # print(act_channel.members)
    return act_channel

    # if len(guild_events) == 0 or all(eachEvent.name != game for eachEvent in guild_events):
    #     play_event = await interaction.guild.create_scheduled_event(name='Checkers Party',
    #                                                                 start_time=discord.utils.utcnow() + timedelta(seconds=60),
    #                                                                 entity_type=discord.EntityType.voice,
    #                                                                 channel=play_channel,
    #                                                                 privacy_level=discord.PrivacyLevel.guild_only,
    #                                                                 reason=f"{interaction.user} started {game}.")