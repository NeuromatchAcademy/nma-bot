import os.path
import json

from discord.ext import commands
import discord
from discord import Intents, Activity, ActivityType

from libs import administrator, verify, interact


# Auth
discordToken = "MTEyMjY2NDMyNTQ4MDQ2NDM4Ng.GYbB-F.6hwrQJj6VfmTNs-QIsFZwLfowFX1Hz6ct0LUEE"


# Load config data.
with open('config.json', 'r') as f:
    roleKey = json.load(f)


# Load portal data.
with open('servers.json') as f:
    master_db = json.load(f)


# Actual Discord bot.
class nmaClient(discord.Client):
    async def on_ready(self):
        for guild in client.guilds:
            for channel in guild.channels:
                if channel.name == "command-center":
                    async for message in channel.history(limit=200):
                        await message.delete()
                    await channel.send(embed=interact.send_embed('master'), view=administrator.CommandDropdownView())
                elif channel.name == 'verify':
                    async for message in channel.history(limit=200):
                        await message.delete()
                    await channel.send(embed=interact.send_embed('verify'))
                elif channel.name == 'activities':
                    async for message in channel.history(limit=200):
                        await message.delete()
                    await channel.send(embed=interact.send_embed('social'), view=administrator.SocialDropdownView())
                elif channel.name == 'bot-log':
                    await channel.send(embed=interact.send_embed('restart'))

        print("\n==============")
        print("Logged in as")
        print(self.user.name)
        print(self.user.id)
        print("==============")

    async def on_message(self, message):

        if message.author != self.user or message.content.startswith("--csrun "):

            if message.channel.name == 'verify' and '@' in message.content:  # If the user sent an email in #verify...
                await verify.verify_user(message)  # ...Attempt verification.
                await message.delete()  # ...Then delete the message.
            elif isinstance(message.channel, discord.DMChannel):  # If the user is DMing the bot...
                await interact.send_embed(message, 'dm')  # ...Send a special message.
            else:  # If the user is neither verifying nor DMing...
                msg_cmd = message.content.split(' ')  # ...Split the message.

                if msg_cmd[0] == '--nma':  # Checking for a command.

                    role = discord.utils.get(message.author.roles, name="NMA Organizers")
                    if role is not None and role.name == 'NMA Organizers':
                        admin = 1
                    else:
                        admin = 0

                    if msg_cmd[1] == 'init' and admin == 1:  # Initialize server's pod channels.
                        await administrator.initialize_server(message.guild)
                    elif msg_cmd[1] in ['assign', 'unassign', 'merge', 'swap'] and admin == 1:
                        await administrator.pod_change(message, msg_cmd[1])
                    elif msg_cmd[1] == 'identify':
                        id_channels = []
                        if 'lgbtq' in msg_cmd[2]:
                            id_channels += [discord.utils.get(message.guild.channels, name="lgbtq-in-neuro")]
                        if 'gender' in msg_cmd[2]:
                            id_channels += [discord.utils.get(message.guild.channels, name="gender-in-neuro")]
                        if 'race' in msg_cmd[2]:
                            id_channels += [discord.utils.get(message.guild.channels, name="race-in-neuro")]

                        for eachChan in id_channels:
                            await eachChan.set_permissions(message.author, view_channel=True, send_messages=True)

                        await message.delete()
                    elif msg_cmd[1] == 'auth':
                        await message.channel.send(f"{message.author} auth status: {admin}.")
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
    message_content=True,
    manage_events=True
)

client = nmaClient(intents=intents)
client.run(discordToken)
activity = discord.Activity(
    name="Studying brains...", type=discord.ActivityType.watching
)
client = discord.Client(activity=activity)
