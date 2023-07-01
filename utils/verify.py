import json
import discord
from . import interact


# Load portal data.
with open('pods.json') as f:
    master_db = json.load(f)

with open('config.json', 'r') as f:
    roleKey = json.load(f)

def find_by_category(nested_dict, target, category, parent_category=None, grandparent_category=None, grand_grandparent_category=None):
    for key, value in nested_dict.items():
        if isinstance(value, dict):
            result = find_by_category(value, target, category, key, parent_category, grandparent_category)
            if result is not None:
                return result
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    result = find_by_category(item, target, category, str(index), key, parent_category)
                    if result is not None:
                        return result
        elif key == category and value == target:
            if parent_category == 'lead_ta':
                return {
                    'name': f"{nested_dict.get('first_name')} {nested_dict.get('last_name')}",
                    'email': nested_dict.get('email'),
                    'role': parent_category,
                    'megapod': grandparent_category
                }
            return {
                'name': f"{nested_dict.get('first_name')} {nested_dict.get('last_name')}",
                'email': nested_dict.get('email'),
                'role': parent_category,
                'pod': grandparent_category,
                'megapod': grand_grandparent_category
            }


async def verify_user(message):
    logChan = discord.utils.get(message.guild.channels, name="bot-log")
    try:
        target_email = message.content
        user = message.author

        print(f"{user} attempting to verify with {message.content}.")

        if 'Climate' in message.guild.name:
            nested_dict = master_db["Computational Tools for Climate Science"]
        elif 'CN' in message.guild.name:
            nested_dict = master_db["Computational Neuroscience"]
        elif 'DL' in message.guild.name:
            nested_dict = master_db["Deep Learning"]

        userInfo = find_by_category(nested_dict, target_email, 'email')

        if len(userInfo["name"]) > 30:
            await user.edit(nick=userInfo["name"][0:30]) # Change user's nickname to full real name.
        else:
            await user.edit(nick=userInfo["name"]) # Change user's nickname to full real name.

        for eachRole in roleKey[userInfo['role']]['roles']: # Assign user appropriate discord roles.
            disc_role = discord.utils.get(message.guild.roles, name=eachRole)
            await user.add_roles(disc_role)

        megapod_cat = discord.utils.get(message.guild.channels,name=f"{userInfo['megapod'].replace(' ', '-')}-general")
        megapod_ta = discord.utils.get(message.guild.channels,name=f"{userInfo['megapod'].replace(' ', '-')}-general")

        if userInfo['role'] != 'lead_ta':
            pod_channel = discord.utils.get(message.guild.channels, name=userInfo["pod"].replace(' ','-'))
            await pod_channel.set_permissions(user, view_channel=roleKey[userInfo['role']]['perms'][0], send_messages=roleKey[userInfo['role']]['perms'][1], manage_messages=roleKey[userInfo['role']]['perms'][2])
            await pod_channel.send(embed=interact.send_embed('custom', "Pod Announcement",f"{userInfo['name']} has joined the pod."))
        else:
            for eachChannel in megapod_cat.channels:
                await eachChannel.set_permissions(user, view_channel=roleKey[userInfo['role']]['perms'][0], send_messages=roleKey[userInfo['role']]['perms'][1], manage_messages=roleKey[userInfo['role']]['perms'][2])

        await megapod_cat.set_permissions(user, view_channel=roleKey[userInfo['role']]['perms'][0], send_messages=roleKey[userInfo['role']]['perms'][1], manage_messages=roleKey[userInfo['role']]['perms'][2])
        await megapod_ta.set_permissions(user, view_channel=roleKey[userInfo['role']]['ta-perms'][0], send_messages=roleKey[userInfo['role']]['ta-perms'][1], manage_messages=roleKey[userInfo['role']]['ta-perms'][2])
        await megapod_cat.send(embed=interact.send_embed('custom', "Megapod Announcement",f"{userInfo['name']} has joined the megapod."))
        await megapod_ta.send(embed=interact.send_embed('custom', "Megapod Announcement",f"TA {userInfo['name']} has joined the megapod."))
        print(f"Verifying user {user} with email {target_email}.")
        if userInfo['role'] != 'lead_ta':
            await logChan.send(f"**Verified:** {message.author} verified for pod {userInfo['pod']}.")
        await logChan.send(f"**Verified:** {message.author} verified for megapod {userInfo['megapod']}.")
    except Exception as error:
        print(f"Verification failed for {message.author} with email {message.content}")
        await logChan.send(f"**Failed Verification:** {message.author} tried to verify with email {message.content}. Ran into this issue: {error}")
