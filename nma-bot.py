import os
import discord
import asyncio
from dotenv import load_dotenv
from pathlib import Path
from utils import administrator, users, interact, db


# Auth
current_dir = Path(__file__).resolve().parent
# parent_dir = current_dir.parent
env_file_path = current_dir / ".env"
load_dotenv(dotenv_path=env_file_path)

discordToken = os.getenv("DISCORD_TOKEN")

## TODO: likely remove this
## Load portal data.
#with open('servers.json') as f:
#    master_db = json.load(f)


# Actual Discord bot.
class nmaClient(discord.Client):

    async def setup_hook(self):
        db.poll_db.start()

    async def on_ready(self):
        for guild in client.guilds:
            for channel in guild.channels:
                if channel.name == "command-center":
                    async for message in channel.history(limit=200):
                        await message.delete()
                    msg = await channel.send(embed=interact.send_embed('master'), view=administrator.CommandDropdownView())
                    await msg.pin()
                elif channel.name == 'verify':
                    async for message in channel.history(limit=200):
                        await message.delete()
                    msg = await channel.send(embed=interact.send_embed('verify'))
                    await msg.pin()
                elif channel.name == 'activity-center':
                    async for message in channel.history(limit=200):
                        await message.delete()
                    msg = await channel.send(embed=interact.send_embed('social'), view=administrator.SocialDropdownView())
                    await msg.pin()
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
                await users.verify_user(message)  # ...Attempt verification.
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
        #elif message.author == self.user and message.channel.name != 'bot-log' and message.pinned == False:
        #    await asyncio.sleep(60)
        #    await message.delete()
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
    voice_states=True
)

client = nmaClient(intents=intents)


async def delete_channel_after(vc):
    bot_chan = discord.utils.get(vc.guild.channels, name='bot-log')
    await bot_chan.send(embed=interact.send_embed('custom', 'Social', f'Voice Channel {vc.name} is empty, deleting after 5 minutes...'))
    print(f'Voice Channel {vc.name} is empty, deleting after 5 minutes...')
    await asyncio.sleep(300)
    if len(vc.members) == 0:
        await bot_chan.send(embed=interact.send_embed('custom', 'Social', f'Deleting channel {vc.name}'))
        print(f'Deleting channel {vc.name}')
        await vc.delete(reason="Inactive for 5 Minutes")


@client.event
async def on_voice_state_update(member, before, after):
    if before.channel:
        chan_cat = before.channel.category.name
        members = before.channel.members
        chan_name = before.channel.name
        if chan_cat == 'social' and len(members) == 0 and 'Social Voice Chat' not in chan_name:
            client.loop.create_task(delete_channel_after(before.channel))


client.run(discordToken)
activity = discord.Activity(
    name="Studying brains...", type=discord.ActivityType.watching
)
client = discord.Client(activity=activity)
