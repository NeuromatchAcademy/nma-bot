import json
import discord
from . import interact


#TODO: create loader funcs
# Load portal data.
# with open('pods.json') as f:
#     master_db = json.load(f)

# with open('discord-ids.json') as f:
#     id_db = json.load(f)

# This might be ok since it does not dynamically change
with open('config.json', 'r') as f:
    roleKey = json.load(f)


async def mega_from_pod(obj, pod):
    course_db = interact.guild_pick(obj)
    for key, values in course_db['structure'].items():
        if pod in values or pod.replace('-', ' ') in values:
            return key
    return 'Pod not found'


async def lookup_user(obj, id):
    with open('discord-ids.json') as f:
        id_db = json.load(f)
    course_db = interact.guild_pick(obj)
    return course_db['users'][id_db[str(id)]]


async def verify_user(message):
    with open('discord-ids.json') as f:
        id_db = json.load(f)
    logChan = discord.utils.get(message.guild.channels, name="bot-log")
    try:
        target_email = message.content.lower()
        user = message.author

        print(f"{user} attempting to verify with {message.content}.")

        nested_dict = interact.guild_pick(message)
        
        # Check if user information exists
        if target_email not in nested_dict['users']:
            raise ValueError("User information not found for this course.")

        userInfo = nested_dict['users'][target_email]
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

        if userInfo['timeslot'] in ['4', '5']:
            time_role = discord.utils.get(message.guild.roles, name='americas')
        elif userInfo['timeslot'] in ['3']:
            time_role = discord.utils.get(message.guild.roles, name='europe-africa')
        elif userInfo['timeslot'] in ['1', '2']:
            time_role = discord.utils.get(message.guild.roles, name='asia-pacific')
        await user.add_roles(time_role)

        id_db[user.id] = target_email

        with open('discord-ids.json', 'w') as f:
            json.dump(id_db, f, ensure_ascii=False, indent=4)

        print(f"Verified user {user} with email {target_email}.")
        await logChan.send(embed=interact.send_embed('custom',"Verified User",f"{message.author} verified for megapod(s) {userInfo['megapods']} and pod(s) {userInfo['pods']}."))
    # ValueError for missing user information
    except ValueError as ve:
        print(f"Verification failed for {message.author} with email {message.content}: {ve}")
        await logChan.send(embed=interact.send_embed('custom', "Failed Verification", f"{message.author} tried to verify with email {message.content}. Reason: {ve}"))
        await message.channel.send(f"Verification failed: {ve}")

    except Exception as error:
        print(f"Verification failed for {message.author} with email {message.content}")
        await logChan.send(embed=interact.send_embed('custom',"Failed Verification",f"{message.author} tried to verify with email {message.content}. Ran into this issue: {error}"))
