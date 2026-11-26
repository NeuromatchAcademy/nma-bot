import asyncio
import json
import logging
import os

import discord

from . import interact
from .constants import TIMESLOT_ROLES
from .paths import data_path

log = logging.getLogger(__name__)

# Serialises read-modify-write of discord-ids.json so concurrent verifications don't lose entries.
_ids_lock = asyncio.Lock()

#TODO: create loader funcs
# Load portal data.
# with open('pods.json') as f:
#     master_db = json.load(f)

# with open(data_path('discord-ids.json')) as f:
#     id_db = json.load(f)

# This might be ok since it does not dynamically change
def load_role_key():
    with open(data_path('config.json'), 'r') as f:
        return json.load(f)


async def mega_from_pod(obj, pod):
    course_db = interact.guild_pick(obj)
    wanted = pod.replace('-', ' ').lower()
    for key, values in course_db['structure'].items():
        if any(v.replace('-', ' ').lower() == wanted for v in values):
            return key
    return 'Pod not found'


async def lookup_user(obj, id):
    with open(data_path('discord-ids.json')) as f:  # noqa: ASYNC230
        id_db = json.load(f)
    course_db = interact.guild_pick(obj)
    return course_db['users'][id_db[str(id)]]


async def verify_user(message):
    roleKey = load_role_key()
    logChan = discord.utils.get(message.guild.channels, name="bot-log")
    try:
        target_email = message.content.strip().lower()
        user = message.author

        log.info("%s attempting to verify with %s", user, message.content)

        nested_dict = interact.guild_pick(message)
        
        # Check if user information exists
        if target_email not in nested_dict['users']:
            raise ValueError("User information not found for this course.")

        userInfo = nested_dict['users'][target_email]
        # Validate before any side effects so a bad record doesn't leave a half-verified user.
        time_role_name = TIMESLOT_ROLES.get(userInfo['timeslot'])
        if time_role_name is None:
            raise ValueError(f"Unknown time slot {userInfo['timeslot']!r}.")

        # bot-log is visible to staff only, so the full details are useful there.
        await logChan.send(embed=interact.send_embed('custom', "Verification DEBUG",
                                                     f"Attempting to verify {message.author} with info {userInfo}."))

        if len(userInfo["name"]) > 30:
            await user.edit(nick=userInfo["name"][0:30]) # Change user's nickname to full real name.
        else:
            await user.edit(nick=userInfo["name"]) # Change user's nickname to full real name.

        for eachRole in roleKey[userInfo['role']]['roles']: # Assign user appropriate discord roles.
            disc_role = discord.utils.get(message.guild.roles, name=eachRole)
            await user.add_roles(disc_role)

        for eachPod in userInfo['pods']:
            pod_channel = discord.utils.get(message.guild.channels, name=eachPod.lower().replace(' ','-'))
            await pod_channel.set_permissions(user, view_channel=roleKey[userInfo['role']]['perms'][0], send_messages=roleKey[userInfo['role']]['perms'][1], manage_messages=roleKey[userInfo['role']]['perms'][2])
            announce = discord.utils.get(pod_channel.threads, name='General')
            await announce.send(embed=interact.send_embed('custom', "Pod Announcement",f"{userInfo['name']} has joined the pod."))

        for eachMega in userInfo['megapods']:
            megapod_gen = discord.utils.get(message.guild.channels,name=f"{eachMega.lower().replace(' ', '-')}-general")
            megapod_ta = discord.utils.get(message.guild.channels,name=f"{eachMega.lower().replace(' ', '-')}-ta-chat")

            await megapod_gen.set_permissions(user, view_channel=roleKey[userInfo['role']]['perms'][0],
                                              send_messages=roleKey[userInfo['role']]['perms'][1],
                                              manage_messages=roleKey[userInfo['role']]['perms'][2])
            await megapod_ta.set_permissions(user, view_channel=roleKey[userInfo['role']]['ta-perms'][0],
                                             send_messages=roleKey[userInfo['role']]['ta-perms'][1],
                                             manage_messages=roleKey[userInfo['role']]['ta-perms'][2])

            await megapod_gen.send(embed=interact.send_embed('custom', "Megapod Announcement",f"{userInfo['role']} {userInfo['name']} has joined the megapod."))

            if userInfo['role'] != 'student':
                await megapod_ta.send(embed=interact.send_embed('custom', "Megapod Announcement",f"{userInfo['role']} {userInfo['name']} has joined the megapod."))

        await user.add_roles(discord.utils.get(message.guild.roles, name=time_role_name))

        await _remember_user(user.id, target_email)

        log.info("Verified user %s with email %s", user, target_email)
        await logChan.send(embed=interact.send_embed('custom',"Verified User",f"{message.author} verified for megapod(s) {userInfo['megapods']} and pod(s) {userInfo['pods']}."))
    # ValueError for missing user information
    except ValueError as ve:
        log.warning("Verification failed for %s with email %s: %s", message.author, message.content, ve)
        await logChan.send(embed=interact.send_embed('custom', "Failed Verification", f"{message.author} tried to verify with email {message.content}. Reason: {ve}"))
    except Exception as error:
        log.exception("Verification failed for %s with email %s", message.author, message.content)
        await logChan.send(embed=interact.send_embed('custom',"Failed Verification",f"{message.author} tried to verify with email {message.content}. Ran into this issue: {error}"))


async def _remember_user(discord_id, email):
    """Record discord id -> email, re-reading the file under a lock to avoid lost updates."""
    path = data_path('discord-ids.json')
    async with _ids_lock:
        try:
            with open(path) as f:  # noqa: ASYNC230
                id_db = json.load(f)
        except FileNotFoundError:
            id_db = {}
        id_db[str(discord_id)] = email
        tmp = path.with_name(path.name + '.tmp')
        with open(tmp, 'w') as f:  # noqa: ASYNC230
            json.dump(id_db, f, ensure_ascii=False, indent=4)
        os.replace(tmp, path)
