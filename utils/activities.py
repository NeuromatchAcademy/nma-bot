import logging
import os
from datetime import timedelta
from pathlib import Path

import aiohttp
import discord
from dotenv import load_dotenv

from .constants import activity_index

log = logging.getLogger(__name__)


class InviteError(RuntimeError):
    """Discord refused to create the activity invite."""

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
        'target_type': 2,  # 2 == InviteTargetType.EmbeddedApplication
        'target_application_id': application_id
    }

    url = f'https://discord.com/api/v9/channels/{channel_id}/invites'

    async with aiohttp.ClientSession() as session, session.post(url, headers=headers, json=body) as resp:
        if resp.status == 200:
            invite = await resp.json()
            log.info('Invite created: https://discord.gg/%s', invite["code"])
            return invite["code"]
        error = await resp.json()
        log.error('Could not create invite for %s (HTTP %s): %s', activity, resp.status, error)
        raise InviteError(f'HTTP {resp.status}')


async def get_activity_channel(
        interaction,
        activity,
        title: str = '',
        count: int = 0
):
    if count == 0 and title == '':
        tmp_title = activity
    elif title == '':
        tmp_title = activity + f"-{count}"
    elif count == 0:
        tmp_title = title
    else:
        tmp_title = title + f"-{count}"

    act_cat = discord.utils.get(interaction.guild.categories, name='social')
    act_channel = discord.utils.get(interaction.guild.channels, name=tmp_title)

    if act_channel is None:
        log.info("Making play channel.")
        act_channel = await interaction.guild.create_voice_channel(name=tmp_title, category=act_cat)
        log.info("Made %s", act_channel)
        return act_channel
    elif len(act_channel.members) < activity_index[activity]['max'] or activity_index[activity]['max'] == 0:
        log.info("Play channel already exists!")
        return act_channel
    elif len(act_channel.members) >= activity_index[activity]['max']:
        log.info("Expanding play channels!")
        act_channel = await get_activity_channel(interaction, activity, title, count + 1)
        return act_channel


# TODO: make the more efficient and auto cancel
async def get_activity_event(interaction, activity, act_channel):
    guild_events = await interaction.guild.fetch_scheduled_events()
    if len(guild_events) == 0 or (activity not in [event.name for event in guild_events]):
        act_event = await interaction.guild.create_scheduled_event(name=activity,
                                                                    start_time=discord.utils.utcnow() + timedelta(
                                                                        seconds=60),
                                                                    entity_type=discord.EntityType.voice,
                                                                    channel=act_channel,
                                                                    privacy_level=discord.PrivacyLevel.guild_only,
                                                                    reason=f"{interaction.user} started {activity}.")
    else:
        act_event = discord.utils.get(interaction.guild.scheduled_events, name=activity)
    return act_event
