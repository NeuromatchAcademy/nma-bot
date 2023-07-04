import json
import discord
from . import interact


# Load portal data.
with open('pods.json') as f:
    master_db = json.load(f)

with open('discord-ids.json') as f:
    id_db = json.load(f)

with open('config.json', 'r') as f:
    roleKey = json.load(f)

async def mega_from_pod(obj, pod):
    course_db = interact.guild_pick(master_db, obj)
    for key, values in course_db['structure'].items():
        if pod in values or pod.replace('-', ' ') in values:
            return key
    return 'Pod not found'

async def lookup_user(obj, id):
    course_db = interact.guild_pick(master_db, obj)
    return course_db['users'][id_db[id]]

async def verify_user(message):
    logChan = discord.utils.get(message.guild.channels, name="bot-log")
    try:
        target_email = message.content
        user = message.author

        print(f"{user} attempting to verify with {message.content}.")

        nested_dict = interact.guild_pick(master_db,message)

        userInfo = nested_dict['users'][target_email]

        if len(userInfo["name"]) > 30:
            await user.edit(nick=userInfo["name"][0:30]) # Change user's nickname to full real name.
        else:
            await user.edit(nick=userInfo["name"]) # Change user's nickname to full real name.

        for eachRole in roleKey[userInfo['role']]['roles']: # Assign user appropriate discord roles.
            disc_role = discord.utils.get(message.guild.roles, name=eachRole)
            await user.add_roles(disc_role)

        for eachPod in userInfo['pods']:
            pod_channel = discord.utils.get(message.guild.channels, name=eachPod.replace(' ','-'))
            await pod_channel.set_permissions(user, view_channel=roleKey[userInfo['role']]['perms'][0], send_messages=roleKey[userInfo['role']]['perms'][1], manage_messages=roleKey[userInfo['role']]['perms'][2])
            announce = discord.utils.get(pod_channel.threads, name='General')
            await announce.send(embed=interact.send_embed('custom', "Pod Announcement",f"{userInfo['name']} has joined the pod."))

        for eachMega in userInfo['megapods']:
            megapod_gen = discord.utils.get(message.guild.channels,name=f"{eachMega.replace(' ', '-')}-general")
            megapod_ta = discord.utils.get(message.guild.channels,name=f"{eachMega.replace(' ', '-')}-ta-chat")

            await megapod_gen.set_permissions(user, view_channel=roleKey[userInfo['role']]['perms'][0],
                                              send_messages=roleKey[userInfo['role']]['perms'][1],
                                              manage_messages=roleKey[userInfo['role']]['perms'][2])
            await megapod_ta.set_permissions(user, view_channel=roleKey[userInfo['role']]['ta-perms'][0],
                                             send_messages=roleKey[userInfo['role']]['ta-perms'][1],
                                             manage_messages=roleKey[userInfo['role']]['ta-perms'][2])

            await megapod_gen.send(embed=interact.send_embed('custom', "Megapod Announcement",f"{userInfo['name']} has joined the megapod."))
            await megapod_ta.send(embed=interact.send_embed('custom', "Megapod Announcement",f"TA {userInfo['name']} has joined the megapod."))

        if userInfo['timeslot'] in [4, 5]:
            time_role = discord.utils.get(message.guild.roles, name='americas')
        elif userInfo['timeslot'] in [3]:
            time_role = discord.utils.get(message.guild.roles, name='europe-africa')
        else:
            time_role = discord.utils.get(message.guild.roles, name='asia-pacific')
        await user.add_roles(time_role)

        id_db[user.id] = target_email

        with open('discord-ids.json', 'w') as f:
            json.dump(id_db, f, ensure_ascii=False, indent=4)


        print(f"Verified user {user} with email {target_email}.")
        await logChan.send(embed=interact.send_embed('custom',"Verified User",f"{message.author} verified for megapod(s) {userInfo['megapods']} and pod(s) {userInfo['pods']}."))
    except Exception as error:
        print(f"Verification failed for {message.author} with email {message.content}")
        await logChan.send(embed=interact.send_embed('custom',"Failed Verification",f"{message.author} tried to verify with email {message.content}. Ran into this issue: {error}"))
