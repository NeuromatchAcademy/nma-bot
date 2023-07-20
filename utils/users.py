import json
import discord
from . import interact
import pandas as pd

# TODO: create loader funcs
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


async def verify_mentor(id_db, logChan, message, email):

    if 'CN' in message.guild.name:
        mentor_file = 'mentors-cn.csv'
    elif 'DL' in message.guild.name:
        mentor_file = 'mentors-dl.csv'

    # load data from csv
    data = pd.read_csv(mentor_file)

    print(data.head())
    head = data.head()
    await logChan.send(embed=interact.send_embed('custom', "Verification DEBUG",
                                                 f"```{head}```"))

    # check if email was found
    if data['mentor'].isin([email]).any():
        match = data[data['mentor'] == email]

        # return the 'podname' corresponding to the matched 'mentor' email
        target_pod = match['podname'].values[0]
        target_pod = target_pod[:-2].lower()

        mentor_role = discord.utils.get(message.guild.roles, name="Mentor")
        user_role = discord.utils.get(message.guild.roles, name="Approved User")
        await message.author.add_roles(mentor_role)
        await message.author.add_roles(user_role)

        pod_channel = discord.utils.get(message.guild.channels, name=target_pod)
        await pod_channel.set_permissions(message.author, view_channel=True, send_messages=True, manage_messages=True)

        id_db[message.author.id] = email

        with open('discord-ids.json', 'w') as f:
            json.dump(id_db, f, ensure_ascii=False, indent=4)

        print(f"Verified user {message.author} with email {email}.")
        await logChan.send(embed=interact.send_embed('custom', "Verified User",
                                                     f"Mentor {message.author} verified for pod `{target_pod}`."))
        return True

    else:
        print(f'{email} does not belong to a mentor.')
        await logChan.send(embed=interact.send_embed('custom', "Verification Failed",
                                                                 f"User {message.author} failed to verify:\nCould not find `{email}` in portal or mentor database."))
        return False


async def verify_user(message):
    with open('discord-ids.json') as f:
        id_db = json.load(f)
    logChan = discord.utils.get(message.guild.channels, name="bot-log")
    target_email = message.content.lower()
    user = message.author

    print(f"{user} attempting to verify with {message.content}.")

    nested_dict = interact.guild_pick(message)

    try:

        if target_email in nested_dict['users']:
            userInfo = nested_dict['users'][target_email]
        else:
            print('Verify mentor triggered')
            await verify_mentor(id_db, logChan, message, target_email)
            return

        if len(userInfo["name"]) > 30:
            await user.edit(nick=userInfo["name"][0:30])  # Change user's nickname to full real name.
        else:
            await user.edit(nick=userInfo["name"])  # Change user's nickname to full real name.

        for eachRole in roleKey[userInfo['role']]['roles']:  # Assign user appropriate discord roles.
            disc_role = discord.utils.get(message.guild.roles, name=eachRole)
            await user.add_roles(disc_role)

        for eachPod in userInfo['pods']:
            pod_channel = discord.utils.get(message.guild.channels, name=eachPod.lower().replace(' ', '-'))
            await pod_channel.set_permissions(user, view_channel=roleKey[userInfo['role']]['perms'][0],
                                              send_messages=roleKey[userInfo['role']]['perms'][1],
                                              manage_messages=roleKey[userInfo['role']]['perms'][2])
            announce = discord.utils.get(pod_channel.threads, name='General')
            await announce.send(
                embed=interact.send_embed('custom', "Pod Announcement", f"{userInfo['name']} has joined the pod."))

        for eachMega in userInfo['megapods']:
            megapod_gen = discord.utils.get(message.guild.channels,
                                            name=f"{eachMega.lower().replace(' ', '-')}-general")
            megapod_ta = discord.utils.get(message.guild.channels, name=f"{eachMega.lower().replace(' ', '-')}-ta-chat")

            await megapod_gen.set_permissions(user, view_channel=roleKey[userInfo['role']]['perms'][0],
                                              send_messages=roleKey[userInfo['role']]['perms'][1],
                                              manage_messages=roleKey[userInfo['role']]['perms'][2])
            await megapod_ta.set_permissions(user, view_channel=roleKey[userInfo['role']]['ta-perms'][0],
                                             send_messages=roleKey[userInfo['role']]['ta-perms'][1],
                                             manage_messages=roleKey[userInfo['role']]['ta-perms'][2])

            await megapod_gen.send(embed=interact.send_embed('custom', "Megapod Announcement",
                                                             f"{userInfo['role']} {userInfo['name']} has joined the megapod."))

            if userInfo['role'] != 'student':
                await megapod_ta.send(embed=interact.send_embed('custom', "Megapod Announcement",
                                                                f"{userInfo['role']} {userInfo['name']} has joined the megapod."))

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
        await logChan.send(embed=interact.send_embed('custom', "Verified User",
                                                     f"{message.author} verified for megapod(s) {userInfo['megapods']} and pod(s) {userInfo['pods']}."))
    except Exception as error:
        print(f"Failed to verify user {user} with email {target_email}.")
        await logChan.send(embed=interact.send_embed('custom', "Failed Verification",
                                                     f"{message.author} failed to verify with emai {target_email} because {error}."))