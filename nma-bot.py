from __future__ import print_function
import os.path
from email.mime.text import MIMEText
from googleapiclient.discovery import build
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import gspread
import logging
import base64
import discord
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import discord
from discord.ext import commands
import random
from dotenv import load_dotenv

import discord_config
from database import GSheetDb

load_dotenv()

# Auth
discordToken = os.getenv("DISCORD_TOKEN")

# Google Set-up
scopeMail = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://mail.google.com/",
]
credsMail = None

db = GSheetDb()
db.connect()

shClient = db.shClient
sheet = db.sheet
df = db.df
dProj = db.dProj

if os.path.exists("token.json"):
    credsMail = Credentials.from_authorized_user_file("token.json", scopeMail)

if not credsMail or not credsMail.valid:
    if credsMail and credsMail.expired and credsMail.refresh_token:
        credsMail.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", scopeMail)
        credsMail = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
        token.write(credsMail.to_json())

service = build("gmail", "v1", credentials=credsMail)
results = service.users().labels().list(userId="me").execute()
labels = results.get("labels", [])

# Logging Set-up
logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)

probDict = {}
chanDict = {}
onbTicks = []
masterEmb = discord.Embed(
    title="",
    url="https://www.neuromatch.io",
    description="Click on the appropriate reactions below to initiate a bot action. If that doesn't work, you can use the commands listed below as a back-up.",
    color=0xA400D1,
)
masterEmb.set_author(
    name="Administrative Interface",
    url="https://www.neuromatch.io",
    icon_url="https://i.imgur.com/NwOh9XV.png",
)
masterEmb.add_field(
    name="Reaction-Based Interface",
    value="To repod a user, click :busts_in_silhouette:.\nTo merge two pods, click :people_hugging:\nTo check a user, click 🕵️.\nTo assign a user to multiple pods, click :zap:.\nTo unassign a user from multiple pods, click :cloud_tornado:.",
    inline=False,
)
masterEmb.add_field(
    name="Pod-Related Commands",
    value="To repod a user, use `--nma repod <discord-id> <user-email> <new-pod>`.   \nTo merge two pods, use `--nma podmerge <old-pod> <new-pod>`. \nTo assign a user to pods, use `--nma assign <user-id> <pod-n>`.                 \nTo unassign a user from pods, use `--nma unassign <user-id> <pod-n>`.     \nTo check who has verified for a pod, use `--nma podcheck` in the pod channel.",
    inline=False,
)
masterEmb.add_field(
    name="Hotfix Commands",
    value="To give interactive students access to all public channels, use `--nma unlock`. \nTo grant lead TAs access to all their pods, use `--nma leadfix`. \nTo restore TA access to their pods, use `--nma tafix`.",
    inline=False,
)
masterEmb.add_field(
    name="Debugging Commands",
    value="To check whether you can use administrative commands, use `--nma auth`.\nTo print all variables to console, use `--nma debug`.",
    inline=False,
)


def create_mail(sender, to, subject, message_text):
    message = MIMEText(message_text)
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes())
    raw = raw.decode()
    return {"raw": raw}


def send_mail(service, user_id, message):
    message = service.users().messages().send(userId=user_id, body=message).execute()
    print("Message Id: %s" % message["id"])
    return message


def embedGen(title, description, student=None):
    if student != None:
        name = student["name"].split(" ")
        pod = student["pod"]
        embed = discord.Embed(
            title=student["name"],
            url="https://neuromatch.io/",
            description=f"Welcome to Neuromatch Academy, {name[0]}!\nYou have been assigned to {pod}.",
            color=0x109319,
        )
        embed.set_thumbnail(url="https://i.imgur.com/hAyp5Vr.png")
        embed.set_footer(
            text="Need help? You can email support@neuromatch.io or open a ticket in #support."
        )
    else:
        embed = discord.Embed(
            title=title,
            url="https://neuromatch.io/",
            description=description,
            color=0x109319,
        )
        # embed.set_thumbnail(url="https://i.imgur.com/hAyp5Vr.png")
        embed.set_footer(
            text="Need help? You can email support@neuromatch.io or open a ticket in #support."
        )
    return embed


def rollcallGen(roll):
    finList = ""
    for user in roll:
        finList += f"\n{user}"
    return finList


# Actual Discord bot.
class nmaClient(discord.Client):
    async def on_ready(self):
        global guild
        global staffRoles
        global allPods
        global logChan
        global allMegas
        global podDict
        global masterSheet
        global masterChan
        global masterMsg
        global veriChan

        guild = client.get_guild(discord_config.guild)

        staffRoles = []
        staffRoles += [guild.get_role(x) for x in discord_config.staffIndex]

        logChan = discord.utils.get(guild.channels, name="bot-log")

        masterChan = discord.utils.get(guild.channels, name="command-center")
        veriChan = discord.utils.get(guild.channels, name="verify")

        async for message in masterChan.history(limit=200):
            await message.delete()

        async for message in veriChan.history(limit=200):
            await message.delete()

        masterMsg = await masterChan.send(embed=masterEmb)
        reactions = ["👥", "🫂", "🕵️", "⚡", "🌪️"]

        for eachReaction in reactions:
            await masterMsg.add_reaction(eachReaction)

        await veriChan.send(
            embed=embedGen(
                "Welcome to the Neuromatch Academy DL Server!",
                "To unlock access to all channels, please copy and paste the email address with which you log into the Neuromatch portal into this chat.",
            )
        )

        masterSheet = pd.DataFrame(sheet.get_all_records())
        print(masterSheet.head())

        podDict = {}
        allPods = list(set(masterSheet["pod"]))
        allMegas = list(set(masterSheet["megapod"]))

        for eachMega in allMegas:
            podDict[eachMega] = []
        for eachPod in masterSheet["pod"]:
            podDict[df.at[df[df["pod"] == eachPod].index.values[0], "megapod"]] += [
                eachPod.replace(" ", "-")
            ]

        print("\n==============")
        print("Logged in as")
        print(self.user.name)
        print(self.user.id)
        print("==============")

    async def on_reaction_add(self, reaction, user):

        if user == self.user:
            return

        cmder = user

        reactionMap = {
            "👥": "repod",
            "🫂": "podmerge",
            "🕵️": "studcheck",
            "⚡": "assign",
            "🌪️": "unassign",
        }

        reqVars = {
            "repod": [
                [
                    "the target user's discord ID",
                    "user's email address",
                    "new pod name (formatted a la 'sneaky-pandas')",
                ],
                ["User:", "User's Email:", "New pod:"],
            ],
            "podmerge": [
                [
                    "the old pod (will be deleted)",
                    "the new pod (which everyone will join)",
                ],
                ["Pod to be deleted:", "New pod:"],
            ],
            "studcheck": [
                ["the discord ID of the user you want to check"],
                ["User's ID:"],
            ],
            "podcheck": [
                [
                    "the name of the pod you want to check (formatted a la 'sneaky-pandas')"
                ],
                ["Pod to be checked:"],
            ],
            "assign": [
                [
                    "the target user's discord ID",
                    "any pods you want to add them to (formatted a la 'sneaky-pandas sweet-spiders open-dogs')",
                ],
                ["User:", "Pods to add them to:"],
            ],
            "unassign": [
                [
                    "the target user's discord ID",
                    "any pods you want to remove them from (formatted a la 'sneaky-pandas sweet-spiders open-dogs')",
                ],
                ["User:", "Pods to remove them from:"],
            ],
        }

        if reaction.message == masterMsg and reaction.message.channel == masterChan:

            await masterMsg.remove_reaction(reaction, user)

            def check(m):
                return m.author == cmder and m.channel == masterChan

            argList = []

            if reaction.emoji in reactionMap.keys():
                for eachPrompt in reqVars[reactionMap[reaction.emoji]][0]:
                    lastPrompt = await masterChan.send(
                        embed=embedGen(
                            "Administrative Message", f"Please send {eachPrompt}."
                        )
                    )
                    reply = await self.wait_for("message", check=check)
                    argList += [reply.content]
                    await reply.delete()
                    await lastPrompt.delete()

                allLines = []
                for eachItem in range(len(argList)):
                    allLines += [
                        f"**{reqVars[reactionMap[reaction.emoji]][1][eachItem]}** {argList[eachItem]}"
                    ]

                finStr = "\n".join(allLines)
                lastPrompt = await masterChan.send(
                    embed=embedGen(
                        "Administrative Message",
                        f'You want to use the {reactionMap[reaction.emoji]} command with the following details:\n\n{finStr}\n\nTo confirm, reply "Y". To cancel, reply "N".',
                    )
                )
                reply = await self.wait_for("message", check=check)
                procRep = reply.content
                if procRep == "Y" or procRep == "y":
                    finCmd = " ".join(argList)
                    cmdMsg = await logChan.send(
                        f"--csrun --nma {reactionMap[reaction.emoji]} {finCmd}"
                    )
                    await cmdMsg.delete()
                    await logChan.send(f"{user.mention}, command has been executed.")

                elif procRep == "N" or procRep == "n":
                    await logChan.send(f"{user.mention}, command has been canceled.")
                else:
                    await logChan.send(
                        f"{user.mention}, invalid response. Command has been canceled."
                    )
                await reply.delete()
                await lastPrompt.delete()

    async def on_message(self, message):

        if message.author != self.user or message.content.startswith("--csrun "):
            if message.content.startswith("--csrun "):
                message.content = message.content[8:]
                print(f"Bot used the command: {message.content}")

            if not message.guild:
                print(f'\nDM received:\n{message.author} said: "{message.content}"')
                await message.channel.send(
                    embed=embedGen(
                        "Warning!",
                        "Hey there.\nIt looks like you tried to send me a direct message. That's no longer support -- instead, please refer to the #verify channel in the NMA server.",
                    )
                )

            if (
                message.channel == veriChan
            ):  # If the message sent in the verification channel...
                print(message.content)
                if (
                    "@" in message.content
                ):  # If the message contains an email address...
                    # await message.add_reaction(discord.utils.get(guild.emojis, name=':load:'))
                    # await message.delete() #Delete the message.

                    print("Student attempting to verify...")
                    errCode = "Verification unsuccessful"
                    errMsg = f"The target user submitted an email that could not be found in the database."

                    try:
                        cellInfo = df[df["email"] == message.content].index.values[0]
                        print("Student identified...")
                        studentInfo = {
                            "name": df.at[cellInfo, "name"],
                            "pod": df.at[cellInfo, "pod"],
                            "role": df.at[cellInfo, "role"],
                            "email": message.content,
                            "megapod": df.at[cellInfo, "megapod"],
                            "timezone": df.at[cellInfo, "timezone"],
                        }
                        studentInfo["pod"] = studentInfo["pod"].replace(" ", "-")
                        targUser = guild.get_member(message.author.id)
                        sheet.update_cell(int(cellInfo + 2), 7, f"{message.author.id}_")
                        if len(studentInfo["name"]) >= 32:
                            studentInfo["name"] = studentInfo["name"][0:30]
                        await targUser.edit(nick=studentInfo["name"])

                        rolesIds = discord_config.Roles.get_roles(studentInfo["role"])
                        if rolesIds:
                            for roleId in rolesIds:
                                await targUser.add_roles(guild.get_role(roleId))
                        else:
                            errCode = "Invalid Role"
                            errMsg = f"Database suggests that {message.author}'s role is {studentInfo['role']}, but there is no matching discord role."
                            raise ValueError

                        if studentInfo["timezone"]:
                            await targUser.add_roles(
                                guild.get_role(
                                    discord_config.Roles.get_timezone_role(
                                        studentInfo["timezone"]
                                    )
                                )
                            )

                        if studentInfo["role"] == "student":
                            if studentInfo["pod"] != "None":
                                podChan = discord.utils.get(
                                    guild.channels, name=studentInfo["pod"]
                                )
                                megaGen = discord.utils.get(
                                    guild.channels,
                                    name=f"{studentInfo['megapod'].replace(' ', '-')}-general",
                                )
                                await podChan.set_permissions(
                                    targUser, view_channel=True, send_messages=True
                                )
                                await podChan.send(
                                    embed=embedGen(
                                        "Pod Announcement",
                                        f"{studentInfo['name']} has joined the pod.",
                                    )
                                )
                                await megaGen.set_permissions(
                                    targUser, view_channel=True, send_messages=True
                                )
                        elif studentInfo["role"] == "TA":
                            if studentInfo["pod"] != "None":
                                podChan = discord.utils.get(
                                    guild.channels, name=studentInfo["pod"]
                                )
                                megaGen = discord.utils.get(
                                    guild.channels,
                                    name=f"{studentInfo['megapod'].replace(' ', '-')}-general",
                                )
                                megaTA = discord.utils.get(
                                    guild.channels,
                                    name=f"{studentInfo['megapod'].replace(' ', '-')}-ta-chat",
                                )
                                await podChan.set_permissions(
                                    targUser,
                                    view_channel=True,
                                    send_messages=True,
                                    manage_messages=True,
                                )
                                await podChan.send(
                                    embed=embedGen(
                                        "Pod Announcement",
                                        f"{studentInfo['name']} has joined the pod.",
                                    )
                                )
                                await megaGen.set_permissions(
                                    targUser, view_channel=True, send_messages=True
                                )
                                await megaTA.set_permissions(
                                    targUser, view_channel=True, send_messages=True
                                )
                        elif studentInfo["role"] == "leadTA":
                            if studentInfo["pod"] != "None":
                                podChan = discord.utils.get(
                                    guild.channels, name=studentInfo["pod"]
                                )
                                megaGen = discord.utils.get(
                                    guild.channels,
                                    name=f"{studentInfo['megapod'].replace(' ', '-')}-general",
                                )
                                megaTA = discord.utils.get(
                                    guild.channels,
                                    name=f"{studentInfo['megapod'].replace(' ', '-')}-ta-chat",
                                )
                                await podChan.set_permissions(
                                    targUser,
                                    view_channel=True,
                                    send_messages=True,
                                    manage_messages=True,
                                )
                                await podChan.send(
                                    embed=embedGen(
                                        "Pod Announcement",
                                        f"{studentInfo['name']} has joined the pod.",
                                    )
                                )
                                await megaGen.set_permissions(
                                    targUser,
                                    view_channel=True,
                                    send_messages=True,
                                    manage_messages=True,
                                )
                                await megaTA.set_permissions(
                                    targUser,
                                    view_channel=True,
                                    send_messages=True,
                                    manage_messages=True,
                                )
                        elif studentInfo["role"] == "projectTA":
                            cellInfo = dProj[
                                dProj["email"] == message.content
                            ].index.values[0]
                            projInfo = {"pods": dProj.at[cellInfo, "pods"]}
                            projPods = projInfo["pods"].split(",")
                            for eachPod in projPods:
                                if eachPod[0].isalpha() == False:
                                    eachPod = eachPod[1:]
                                podChan = discord.utils.get(
                                    guild.channels, name=eachPod.replace(" ", "-")
                                )
                                await podChan.set_permissions(
                                    targUser, view_channel=True, send_messages=True
                                )
                                megaGen = discord.utils.get(
                                    guild.channels,
                                    name=f"{df.at[df[df['pod']==eachPod.replace('-',' ')].index.values[0],'megapod'].replace(' ', '-')}-general",
                                )
                                await megaGen.set_permissions(
                                    targUser, view_channel=True, send_messages=True
                                )
                            studentInfo["pod"] = projPods

                        if (
                            any(
                                guild.get_role(x) in message.author.roles
                                for x in discord_config.staffIndex
                            )
                            == True
                        ):
                            print(f"{message.author} not silenced.")
                        else:
                            await message.delete()  # Delete the message.
                        await logChan.send(
                            embed=embedGen(
                                "Administrative Message",
                                f"{message.author} successfully verified.",
                            )
                        )  # Log the issue.'''

                        print("Could not register discord ID in database.")

                        # This bit is for verification confirmation emails.
                        # veriMail = create_mail('discordsupport@neuromatch.io',studentInfo['email'],'Discord Verification Completed.','You have successfully verified your identity on the NMA discord.')
                        # send_mail(service,'me',veriMail)

                        print("Verification processed.\n")

                    except:  # If something goes wrong during verification...
                        if message.author.id not in probDict.keys():
                            probDict[message.author.id] = 1
                        else:
                            probDict[message.author.id] += 1
                            if probDict[message.author.id] == 2:
                                await logChan.send(
                                    embed=embedGen(
                                        "Warning!",
                                        f"{message.author} has failed to verify twice now. Please investigate.",
                                    )
                                )  # Log the issue.'''
                            elif probDict[message.author.id] > 2:
                                suppRole = guild.get_role(discord_config.Roles.support)
                                adminCat = discord.utils.get(
                                    guild.categories, name="administrative"
                                )
                                newChan = await guild.create_text_channel(
                                    f"onboard-ticket-{str(message.author)[:5]}",
                                    category=adminCat,
                                )  # Create a channel dedicated to the mucked-up verification.
                                await newChan.set_permissions(
                                    guild.default_role,
                                    view_channel=False,
                                    send_messages=False,
                                )  # Set up permissions so the channel is private.
                                await newChan.set_permissions(
                                    message.author,
                                    view_channel=True,
                                    send_messages=True,
                                )  # Grant the problem user access to the new channel.

                                def check(reaction, user):
                                    return (
                                        str(reaction.emoji) == "🔒"
                                        and str(reaction.message.channel)[:7]
                                        == "onboard"
                                    )

                                errIni = await newChan.send(
                                    embed=embedGen(
                                        f"{errCode}",
                                        f"{errMsg}...\nIf no one assists you within the next two hours, please contact support@neuromatch.io.\nClick the 🔒 reaction to close this ticket.",
                                    )
                                )  # Send an error message.
                                await errIni.add_reaction("🔒")
                                reaction, user = await client.wait_for(
                                    "reaction_add", check=check
                                )
                                await logChan.send(
                                    embed=embedGen(
                                        "Warning!",
                                        f"{message.author} unsuccessfully tried to verify with the following message:\n{message.content}\nPlease reach out and investigate @ #{newChan}.",
                                    )
                                )  # Log the issue.'''
                                probDict[message.author.id] = -9

                        print("Verification failed.\n")
                        # await message.add_reaction(discord.utils.get(guild.emojis, name='x'))
                        if (
                            any(
                                guild.get_role(x) in message.author.roles
                                for x in discord_config.staffIndex
                            )
                            == True
                        ):
                            print(f"{message.author} not silenced.")
                        else:
                            await message.delete()  # Delete the message.await message.delete() #Delete the message.

                else:
                    if (
                        any(
                            guild.get_role(x) in message.author.roles
                            for x in discord_config.staffIndex
                        )
                        == True
                    ):
                        print(f"{message.author} not silenced.")
                    else:
                        await message.delete()  # Delete the message.await message.delete() #Delete the message.

            if message.content.startswith(
                "--nma "
            ):  # If the message contains a command...

                cmder = guild.get_member(
                    message.author.id
                )  # Grab the discord user trying to use the command.
                cmd = message.content[6:]  # Trim the message.

                if cmd.startswith(
                    "init"
                ):  # This command creates channel categories and pod channels for all pods and megapods in the bot's database.
                    if message.author.id == discord_config.admin:
                        print("Initializing server...\n")
                        for eachMega in podDict.keys():
                            podDict[eachMega] = set(podDict[eachMega])
                            await guild.create_category(eachMega)
                            megaCat = discord.utils.get(guild.categories, name=eachMega)

                            newChan = await guild.create_text_channel(
                                f"{eachMega.replace(' ','-')}-general", category=megaCat
                            )
                            await newChan.set_permissions(
                                guild.default_role,
                                view_channel=False,
                                send_messages=False,
                            )
                            newChan = await guild.create_text_channel(
                                f"{eachMega.replace(' ','-')}-ta-chat", category=megaCat
                            )
                            await newChan.set_permissions(
                                guild.default_role,
                                view_channel=False,
                                send_messages=False,
                            )

                            for eachPod in podDict[eachMega]:
                                try:
                                    newChan = await guild.create_text_channel(
                                        f"{eachPod}", category=megaCat
                                    )
                                    await newChan.set_permissions(
                                        guild.default_role,
                                        view_channel=False,
                                        send_messages=False,
                                    )
                                    for eachRole in staffRoles:
                                        await newChan.set_permissions(
                                            eachRole,
                                            view_channel=True,
                                            send_messages=True,
                                        )
                                except:
                                    await logChan.send(
                                        embed=embedGen(
                                            "Administrative Message.",
                                            f"Channel creation failed for {eachPod}.",
                                        )
                                    )

                            await logChan.send(
                                embed=embedGen(
                                    "Administrative Message.",
                                    f"SERVER INITIALIZATION COMPLETE.",
                                )
                            )
                            print("Server initialization complete.")
                    else:
                        await message.channel.send(
                            embed=embedGen(
                                "Administrative Message.", f"Only Kevin can do this."
                            )
                        )

                elif cmd.startswith(
                    "assign"
                ):  # Grants given user access to all pod channels mentioned and their respective megapods.
                    cmdMsg = cmd.split(" ")
                    targUser = discord.utils.get(guild.members, id=int(cmdMsg[1]))
                    for eachPod in cmdMsg:
                        if (
                            eachPod != targUser
                            and eachPod != cmdMsg[1]
                            and eachPod != "--nma"
                            and eachPod != "assign"
                        ):
                            try:
                                podChan = discord.utils.get(
                                    guild.channels, name=eachPod
                                )
                                megaGen = discord.utils.get(
                                    guild.channels,
                                    name=f"{df.at[df[df['pod']==eachPod.replace('-',' ')].index.values[0],'megapod'].replace(' ', '-')}-general",
                                )
                                await megaGen.set_permissions(
                                    targUser, view_channel=True, send_messages=True
                                )
                                await podChan.set_permissions(
                                    targUser, view_channel=True, send_messages=True
                                )
                                await podChan.send(
                                    embed=embedGen(
                                        "Pod Announcement",
                                        f"{targUser} has joined the pod.",
                                    )
                                )
                                await logChan.send(
                                    embed=embedGen(
                                        "Administrative Message",
                                        f"{targUser} was successfully assigned to {eachPod}.",
                                    )
                                )
                            except:
                                await logChan.send(
                                    embed=embedGen(
                                        "WARNING!",
                                        f"Could not add {targUser} to pod-{eachPod}.",
                                    )
                                )

                elif cmd.startswith(
                    "unassign"
                ):  # Removes given user's access to all pod channels mentioned and their respective megapods.
                    cmdMsg = cmd.split(" ")
                    targUser = discord.utils.get(guild.members, id=int(cmdMsg[1]))
                    for eachPod in cmdMsg:
                        if (
                            eachPod != targUser
                            and eachPod != "--nma"
                            and eachPod != "unassign"
                        ):
                            try:
                                podChan = discord.utils.get(
                                    guild.channels, name=eachPod
                                )
                                megaGen = discord.utils.get(
                                    guild.channels,
                                    name=f"{df.at[df[df['pod']==eachPod.replace('-',' ')].index.values[0],'megapod'].replace(' ', '-')}-general",
                                )
                                await megaGen.set_permissions(
                                    targUser, view_channel=False, send_messages=False
                                )
                                await podChan.set_permissions(
                                    targUser, view_channel=False, send_messages=False
                                )
                                await podChan.send(
                                    embed=embedGen(
                                        "Pod Announcement",
                                        f"{targUser} has left the pod.",
                                    )
                                )
                                await logChan.send(
                                    embed=embedGen(
                                        "Administrative Message",
                                        f"{targUser} was successfully removed from {eachPod}.",
                                    )
                                )
                            except:
                                await logChan.send(
                                    embed=embedGen(
                                        "WARNING!",
                                        f"Could not remove {targUser} from pod-{eachPod}.",
                                    )
                                )

                elif cmd.startswith("identify"):
                    targUser = cmder
                    queerChan = discord.utils.get(guild.channels, name="lgbtq-in-neuro")
                    genderChan = discord.utils.get(
                        guild.channels, name="gender-in-neuro"
                    )
                    raceChan = discord.utils.get(guild.channels, name="race-in-neuro")
                    if "lgbtq" in cmd:
                        await queerChan.set_permissions(
                            targUser, view_channel=True, send_messages=True
                        )
                        await message.delete()
                    elif "gender" in cmd:
                        await genderChan.set_permissions(
                            targUser, view_channel=True, send_messages=True
                        )
                        await message.delete()
                    elif "race" in cmd:
                        await raceChan.set_permissions(
                            targUser, view_channel=True, send_messages=True
                        )
                        await message.delete()

                elif cmd.startswith(
                    "auth"
                ):  # Debugging command that tells the user whether they are authorized to use administrative commands.
                    await message.channel.send(
                        embed=embedGen(
                            "Administrative Message.",
                            f"Authorized user recognized: <@{message.author.id}>.",
                        )
                    )

                elif cmd.startswith(
                    "debug"
                ):  # Debug command that prints a bunch of variables in the console.
                    debugCont = {
                        "Current message channel": message.channel,
                        "chanDict": chanDict,
                        "staffRoles": staffRoles,
                        "podDict": podDict,
                        "allPods": allPods,
                        "allMegas": allMegas,
                        "podCount": len(allPods),
                    }
                    for allCont in debugCont.keys():
                        try:
                            print(f"{allCont}:\n{debugCont[allCont]}\n")
                        except:
                            print(f"Failed to grab {allCont}\n")
                    await logChan.send(
                        embed=embedGen(
                            "Administrative Message.",
                            "Debugging requested. Check console log for details.",
                        )
                    )

                elif cmd.startswith(
                    "repod"
                ):  # Reassings the given user to the given pod.
                    cmdMsg = cmd.split(" ")
                    targUser = cmdMsg[1]
                    targMail = cmdMsg[2]
                    targPod = cmdMsg[3]

                    try:
                        cellInfo = df[df["email"] == targMail].index.values[0]
                        print("Student identified...")
                        studentInfo = {
                            "name": df.at[cellInfo, "name"],
                            "pod": df.at[cellInfo, "pod"],
                            "role": df.at[cellInfo, "role"],
                            "email": targMail,
                            "megapod": df.at[cellInfo, "megapod"],
                            "timezone": df.at[cellInfo, "timezone"],
                        }
                        print(studentInfo)
                        prevTZ = studentInfo["timezone"]
                        studentInfo["timezone"] = df.at[
                            df[df["pod"] == targPod.replace("-", " ")].index.values[0],
                            "timezone",
                        ]
                        prevChan = discord.utils.get(
                            guild.channels, name=studentInfo["pod"].replace(" ", "-")
                        )
                        prevMegaGen = discord.utils.get(
                            guild.channels,
                            name=f"{studentInfo['megapod'].replace(' ', '-')}-general",
                        )
                        prevMegaTA = discord.utils.get(
                            guild.channels,
                            name=f"{studentInfo['megapod'].replace(' ', '-')}-ta-chat",
                        )
                        targUser = discord.utils.get(guild.members, id=int(targUser))
                        podChan = discord.utils.get(guild.channels, name=targPod)
                        megaGen = discord.utils.get(
                            guild.channels,
                            name=f"{df.at[df[df['pod']==targPod.replace('-',' ')].index.values[0],'megapod'].replace(' ', '-')}-general",
                        )
                        megaTA = discord.utils.get(
                            guild.channels,
                            name=f"{df.at[df[df['pod']==targPod.replace('-',' ')].index.values[0],'megapod'].replace(' ', '-')}-ta-chat",
                        )
                        # print(f'targUser = {targUser}\ntargMail = {targMail}\ntargPod = {targPod}\nprevChan = {prevChan}\nprevMegaGen = {prevMegaGen}\nprevMegaTA = {prevMegaTA}\nmegaGen = {megaGen}\nmegaTA = {megaTA}')
                        await targUser.add_roles(
                            guild.get_role(
                                discord_config.Roles.get_timezone_role(
                                    studentInfo["timezone"]
                                )
                            )
                        )
                        await targUser.remove_roles(
                            guild.get_role(
                                discord_config.Roles.get_timezone_role(prevTZ)
                            )
                        )
                        await megaGen.set_permissions(
                            targUser, view_channel=True, send_messages=True
                        )
                        await podChan.set_permissions(
                            targUser, view_channel=True, send_messages=True
                        )
                        await prevChan.set_permissions(
                            targUser, view_channel=False, send_messages=False
                        )
                        await prevMegaGen.set_permissions(
                            targUser, view_channel=False, send_messages=False
                        )
                        await prevMegaTA.set_permissions(
                            targUser, view_channel=False, send_messages=False
                        )
                        await targUser.edit(nick=studentInfo["name"])

                        rolesIds = discord_config.Roles.get_roles(studentInfo["role"])
                        if rolesIds:
                            for roleId in rolesIds:
                                await targUser.add_roles(guild.get_role(roleId))
                        else:
                            errCode = "Invalid Role"
                            errMsg = f"Database suggests that {message.author}'s role is {studentInfo['role']}, but there is no matching discord role."
                            raise ValueError

                        if studentInfo["timezone"]:
                            await targUser.add_roles(
                                guild.get_role(
                                    discord_config.Roles.get_timezone_role(
                                        studentInfo["timezone"]
                                    )
                                )
                            )

                        if studentInfo["role"] == "student":
                            if studentInfo["pod"] != "None":
                                await podChan.set_permissions(
                                    targUser, view_channel=True, send_messages=True
                                )
                                await podChan.send(
                                    embed=embedGen(
                                        "Pod Announcement",
                                        f"{studentInfo['name']} has joined the pod.",
                                    )
                                )
                                await megaGen.set_permissions(
                                    targUser, view_channel=True, send_messages=True
                                )
                        elif studentInfo["role"] == "TA":
                            if studentInfo["pod"] != "None":
                                await podChan.set_permissions(
                                    targUser,
                                    view_channel=True,
                                    send_messages=True,
                                    manage_messages=True,
                                )
                                await podChan.send(
                                    embed=embedGen(
                                        "Pod Announcement",
                                        f"{studentInfo['name']} has joined the pod.",
                                    )
                                )
                                await megaGen.set_permissions(
                                    targUser, view_channel=True, send_messages=True
                                )
                                await megaTA.set_permissions(
                                    targUser, view_channel=True, send_messages=True
                                )
                        elif studentInfo["role"] == "leadTA":
                            if studentInfo["pod"] != "None":
                                await podChan.set_permissions(
                                    targUser,
                                    view_channel=True,
                                    send_messages=True,
                                    manage_messages=True,
                                )
                                await podChan.send(
                                    embed=embedGen(
                                        "Pod Announcement",
                                        f"{studentInfo['name']} has joined the pod.",
                                    )
                                )
                                await megaGen.set_permissions(
                                    targUser,
                                    view_channel=True,
                                    send_messages=True,
                                    manage_messages=True,
                                )
                                await megaTA.set_permissions(
                                    targUser,
                                    view_channel=True,
                                    send_messages=True,
                                    manage_messages=True,
                                )

                        await logChan.send(
                            embed=embedGen(
                                "User Repodded!",
                                f"{studentInfo['role']} {studentInfo['name']} has been successfully moved to {targPod} and can now access the appropriate channels.",
                            )
                        )

                    except:
                        await logChan.send(
                            embed=embedGen("WARNING!", "Repodding failed.")
                        )

                elif cmd.startswith(
                    "podmerge"
                ):  # Merges the two pods by deleting the first one mentioned and migrating its users to the second one mentioned.
                    cmdMsg = cmd.split(" ")
                    oldPod = discord.utils.get(guild.channels, name=cmdMsg[1])
                    newPod = discord.utils.get(guild.channels, name=cmdMsg[2])
                    rollCall = []
                    staffCount = 0
                    totalCount = 0
                    for user in oldPod.members:
                        if (
                            any(
                                guild.get_role(x) in user.roles
                                for x in discord_config.staffIndex
                                + [discord_config.staffId]
                            )
                            == True
                        ):
                            staffCount += 1
                            continue
                        else:
                            try:
                                await oldPod.set_permissions(
                                    user, view_channel=False, send_messages=False
                                )
                                await newPod.set_permissions(
                                    user, view_channel=True, send_messages=True
                                )
                                totalCount += 1
                            except:
                                continue
                    await message.channel(
                        embed=embedGen(
                            "Administrative Message",
                            f"Successfully moved {totalCount} out of {len(oldPod.members)} users to {cmdMsg[2]}.",
                        )
                    )
                    if len(oldPod.members) <= staffCount:
                        try:
                            await oldPod.delete()
                        except:
                            await message.channel(
                                embed=embedGen(
                                    "Administrative Message.",
                                    f"Could not delete channel {cmdMsg[1]}.",
                                )
                            )

                elif cmd.startswith(
                    "tafix"
                ):  # Grants all teaching assistants access to the appropriate pods should it somehow be lost.
                    for eachChannel in guild.channels:
                        if " " in str(eachChannel):
                            continue
                        else:
                            for entity, overwrite in eachChannel.overwrites.items():
                                if overwrite.manage_messages:
                                    if str(entity) not in [
                                        "@everyone",
                                        "NMA Staffers",
                                        "Interactive Student",
                                        "NMA Organizers",
                                        "Robots",
                                    ]:
                                        if (
                                            all(
                                                guild.get_role(x) in entity.roles
                                                for x in discord_config.taIds
                                            )
                                            == False
                                        ):
                                            try:
                                                await eachChannel.set_permissions(
                                                    entity,
                                                    view_channel=True,
                                                    send_messages=True,
                                                    manage_messages=True,
                                                )
                                                await logChan.send(
                                                    embed=embedGen(
                                                        "Administrative Message",
                                                        f"TA {entity} has regained access to pod {eachChannel}.",
                                                    )
                                                )
                                            except:
                                                await logChan.send(
                                                    embed=embedGen(
                                                        "Administrative Message",
                                                        f"Could not grant TA {entity} to pod {eachChannel}.",
                                                    )
                                                )

                elif cmd.startswith(
                    "leadfix"
                ):  # Grants all lead TAs access to all the pod channels they supervise.
                    for eachMega in set(allMegas):
                        if eachMega != None and eachMega != "None" and eachMega != "":
                            print(eachMega)
                            megaLead = "NOT FOUND"
                            megaGen = eachMega.replace(" ", "-")
                            megaTA = discord.utils.get(
                                guild.channels, name=f"{megaGen}-general"
                            )
                            megaGen = discord.utils.get(
                                guild.channels, name=f"{megaGen}-ta-chat"
                            )
                            for user in megaGen.members:
                                if (
                                    guild.get_role(discord_config.Roles.leadTa)
                                    in user.roles
                                ):
                                    megaLead = user
                                else:
                                    continue
                            for eachPod in set(podDict[eachMega]):
                                try:
                                    podChan = discord.utils.get(
                                        guild.channels, name=eachPod
                                    )
                                    await podChan.set_permissions(
                                        megaLead,
                                        view_channel=True,
                                        send_messages=True,
                                        manage_messages=True,
                                    )
                                    await megaTA.set_permissions(
                                        megaLead, view_channel=True, send_messages=True
                                    )
                                except:
                                    if megaLead == "NOT FOUND":
                                        await logChan.send(
                                            embed=embedGen(
                                                "Administrative Message.",
                                                f"No lead TA found for pod-{podChan}.",
                                            )
                                        )
                                    else:
                                        await logChan.send(
                                            embed=embedGen(
                                                "Administrative Message.",
                                                f"Could not grant Lead TA {megaLead} access to pod-{podChan}.",
                                            )
                                        )
                        else:
                            continue

                elif cmd.startswith("podcheck"):
                    try:
                        rollCall = []
                        for user in message.channel.members:
                            if (
                                any(
                                    guild.get_role(x) in user.roles
                                    for x in discord_config.staffIndex
                                    + [discord_config.staffId]
                                )
                                == True
                            ):
                                continue
                            else:
                                if user.nick == None:
                                    rollCall += [user]
                                else:
                                    rollCall += [user.nick]
                        if len(rollCall) == 0:
                            await message.channel.send(
                                embed=embedGen(
                                    "Administrative Message.",
                                    f"Uh-oh. The only people in this channel are administrators, support staff, and robots. If that's wrong, please open a tech ticket in #support.",
                                )
                            )
                        else:
                            await message.channel.send(
                                embed=embedGen(
                                    "Pod Rollcall.",
                                    f"TA {cmder} requested a rollcall.\nThe following members have verified for this pod:\n{rollcallGen(rollCall)}.",
                                )
                            )
                    except:
                        await message.channel.send(
                            embed=embedGen(
                                "Administrative Message.",
                                f"That didn't work. Please note that this command may only be used in pod channels.",
                            )
                        )

                elif cmd.startswith("zoombatch"):
                    zoomies = shClient.open("Zooms").sheet1
                    zoomRecs = zoomies.get_all_records()
                    dZoom = pd.DataFrame.from_dict(zoomRecs)
                    for eachVal in dZoom["pod_name"]:
                        zoomLink = dZoom[dZoom["pod_name"] == eachVal].index.values[0]
                        zoomLink = dZoom.at[zoomLink, "zoom_link"]
                        podChannel = discord.utils.get(
                            guild.channels, name=eachVal.replace(" ", "-")
                        )
                        async for eaMessage in podChannel.history(limit=10):
                            if eaMessage.author == self.user:
                                await eaMessage.delete()
                        zoomRem = await podChannel.send(
                            embed=embedGen(
                                "Zoom Reminder",
                                f"The zoom link for {eachVal} is\n{zoomLink}\n\nNew to discord? Read our guide: https://docs.google.com/document/d/1a5l6QVhuqYnwFR090yDnQGhHSA3u2IEwOs0JZwkfyLo/edit?usp=sharing",
                            )
                        )
                        await zoomRem.pin()

                elif cmd.startswith("studcheck"):
                    cmdMsg = cmd.split(" ")
                    targID = cmdMsg[1]
                    targUser = discord.utils.get(guild.members, id=int(targID))
                    targID = f"{targID}_"
                    pod = None

                    if targID in df["discord id"].tolist():
                        try:
                            cellInfo = df[df["discord id"] == targID].index.values[0]

                            studentInfo = {
                                "name": df.at[cellInfo, "name"],
                                "pod": df.at[cellInfo, "pod"],
                                "role": df.at[cellInfo, "role"],
                                "email": df.at[cellInfo, "email"],
                                "megapod": df.at[cellInfo, "megapod"],
                                "timezone": df.at[cellInfo, "timezone"],
                            }

                            if studentInfo["role"] == "student":
                                for eachPod in set(allPods):
                                    if eachPod == None or eachPod == "None":
                                        continue
                                    podChan = discord.utils.get(
                                        guild.channels, name=eachPod.replace(" ", "-")
                                    )
                                    if targUser in podChan.members:
                                        pod = eachPod

                                if pod == None:
                                    pod = studentInfo["pod"]

                                if pod == studentInfo["pod"]:
                                    repod = 0
                                    megapod = studentInfo["megapod"]
                                else:
                                    repod = 1
                                    megapod = list(podDict.keys())[
                                        list(podDict.values()).index(
                                            pod.replace(" ", "-")
                                        )
                                    ]
                            else:
                                pod = studentInfo["pod"]
                                megapod = studentInfo["megapod"]
                                repod = 0

                            infEmbed = discord.Embed(
                                title="", url="https://i.imgur.com/hAyp5Vr.png"
                            )
                            infEmbed.set_author(
                                name="User Breakdown",
                                icon_url="https://i.imgur.com/hAyp5Vr.png",
                            )
                            infEmbed.set_thumbnail(url=targUser.avatar_url)
                            infEmbed.add_field(
                                name=f"Name: {studentInfo['name']}",
                                value=f"Email: {studentInfo['email']} \nPod: {pod}\nMegapod: {megapod}\nTimezone: {studentInfo['timezone']}",
                                inline=True,
                            )
                            if repod == 1:
                                infEmbed.add_field(
                                    name=f"Notes",
                                    value=f"User was repodded from {studentInfo['pod']} to {pod}.",
                                    inline=False,
                                )
                            infEmbed.set_footer(text="Need help? Tag Kevin.")

                            await logChan.send(embed=infEmbed)
                        except:
                            await logChan.send(
                                embed=embedGen(
                                    "Administrative Message",
                                    "User ID was found, but something went wrong during retrieval.",
                                )
                            )
                    else:
                        await logChan.send(
                            embed=embedGen(
                                "Administrative Message",
                                "User ID not found in database.",
                            )
                        )

                elif cmd.startswith("idgrab"):
                    print("idgrab triggered.")

                    noNicks = []
                    pronouns = []
                    failUser = []

                    foundCount = 0

                    try:
                        for eachUser in guild.members:
                            if guild.get_role(discord_config.staffId) in eachUser.roles:
                                continue
                            if eachUser.nick == None:

                                if len(eachUser.name.split(" ")) <= 1:
                                    continue

                                for eachVar in [
                                    eachUser.name,
                                    eachUser.name.lower(),
                                    eachUser.name.upper(),
                                    eachUser.name[:-1],
                                    f"{eachUser.name} ",
                                ]:
                                    try:
                                        foundCount += 1
                                        cellInfo = df[
                                            df["name"] == eachVar
                                        ].index.values[0]
                                        df.at[
                                            cellInfo, "discord id"
                                        ] = f"{eachUser.id}_"
                                    except:
                                        pass

                            else:
                                if (
                                    any(
                                        x.lower() in str(eachUser.nick).lower()
                                        for x in [
                                            "him",
                                            "her",
                                            "they",
                                            "[",
                                            "]",
                                            ")",
                                            "(",
                                            "(she/her)",
                                            "(he)",
                                            "(he/him)",
                                            "[she/her]",
                                            "[he/him]",
                                            "/",
                                            "\\",
                                        ]
                                    )
                                    == True
                                ):

                                    searchTerm = eachUser.nick.split(" ")

                                    if len(searchTerm) <= 2:
                                        continue

                                    searchTerm = eachUser.nick.removesuffix(
                                        searchTerm[-1]
                                    )

                                    for eachVar in [
                                        searchTerm,
                                        searchTerm.lower(),
                                        searchTerm.upper(),
                                        searchTerm[:-1],
                                        f"{searchTerm} ",
                                    ]:
                                        try:
                                            foundCount += 1
                                            cellInfo = df[
                                                df["name"] == eachVar
                                            ].index.values[0]
                                            df.at[
                                                cellInfo, "discord id"
                                            ] = f"{eachUser.id}_"
                                        except:
                                            pass

                                else:
                                    if (
                                        any(df["name"].str.contains(eachUser.nick))
                                        == True
                                        or any(
                                            df["name"].str.contains(
                                                str(eachUser.nick).lower()
                                            )
                                        )
                                        == True
                                    ):
                                        for eachVar in [
                                            eachUser.nick,
                                            eachUser.nick.lower(),
                                            eachUser.nick.upper(),
                                            eachUser.nick[:-1],
                                            f"{eachUser.nick} ",
                                        ]:
                                            try:
                                                foundCount += 1
                                                cellInfo = df[
                                                    df["name"] == eachVar
                                                ].index.values[0]
                                                df.at[
                                                    cellInfo, "discord id"
                                                ] = f"{eachUser.id}_"
                                            except:
                                                pass

                        sheet.update([df.columns.values.tolist()] + df.values.tolist())
                        print(f"Finished {foundCount} IDs.")
                    except:
                        print("Failed idgrab.")

                elif cmd.startswith(
                    "unlock"
                ):  # Gives interactive students access to all public channels.
                    for chanCat in [
                        discord.utils.get(guild.categories, id=catID)
                        for catID in discord_config.categories
                    ]:
                        for eachChan in chanCat.channels:
                            await eachChan.set_permissions(
                                guild.get_role(
                                    discord_config.Roles.interactive_student
                                ),
                                view_channel=True,
                                send_messages=True,
                            )

                elif cmd.startswith("update"):
                    os.execv(sys.executable, ["python"] + sys.argv)

                elif cmd.startswith("quit"):
                    quit()

                else:
                    await message.channel.send(
                        embed=embedGen(
                            "Warning!", f"Command {cmd.split(' ')[0]} does not exist."
                        )
                    )

        else:
            return


description = "The official NMA Discord Bot."
intents = discord.Intents(
    messages=True,
    guilds=True,
    typing=True,
    members=True,
    presences=True,
    reactions=True,
)

client = nmaClient(intents=intents)
client.run(discordToken)
activity = discord.Activity(
    name="Studying brains...", type=discord.ActivityType.watching
)
client = discord.Client(activity=activity)
