import os
import sys
import discord
from discord import app_commands
import asyncio
from dotenv import load_dotenv
from pathlib import Path
from utils import administrator, users, interact, db, activities
import pandas as pd

# Auth
current_dir = Path(__file__).resolve().parent
# parent_dir = current_dir.parent
env_file_path = current_dir / ".env"
load_dotenv(dotenv_path=env_file_path)

discordToken = os.getenv("DISCORD_TOKEN")


@app_commands.command()
@app_commands.describe(activity='activity to play')
@app_commands.choices(activity=[
    app_commands.Choice(name='🏁 Checkers', value='Checkers In The Park'),
    app_commands.Choice(name='⛳ Minigolf', value='Putt Party'),
    app_commands.Choice(name='🤣 Know What I Meme', value='Know What I Meme'),
    app_commands.Choice(name='♟️ Chess', value='Chess In The Park'),
    app_commands.Choice(name='☎️ Gartic Phone', value='Gartic Phone'),
    app_commands.Choice(name='⚽ Soccer', value='Bobble League'),
    app_commands.Choice(name='⚒️ Land-io', value='Land-io'),
    app_commands.Choice(name='✏️ Pictionary', value='Sketch Heads'),
    app_commands.Choice(name='🃏 Blazing 8s', value='Blazing 8s'),
    app_commands.Choice(name='🤔 Crosswords', value='SpellCast'),
    app_commands.Choice(name='🅱️ Scrabble', value='Scrabble'),
    app_commands.Choice(name='♣️ Poker', value='Poker Night'),
    app_commands.Choice(name='🖊️ Whiteboard', value='Jamspace'),
])
async def start_activity(interaction: discord.Interaction, activity: app_commands.Choice[str]):
    if interaction.channel.category.name.lower() not in ['observer track', 'alumni', 'administrative',
                                                         'teaching assistants', 'content help',
                                                         'projects', 'information', 'lobby',
                                                         'professional development', 'social', 'contest',
                                                         'diversity', 'python precourse', 'earth expo']:
        await interaction.response.send_message(f'This may take a second. Please be patient, {interaction.user}!',
                                                ephemeral=True)
        game = activity.value
        game_cat = interaction.channel.category
        game_channel = discord.utils.get(game_cat.channels, name='megapod-games')
        gen_channel = discord.utils.get(game_cat.channels, name=f'{game_cat.name.lower()}-general')
        if game_channel is None:
            game_channel = await game_cat.create_voice_channel('megapod-games')
            await game_channel.set_permissions(interaction.guild.default_role, view_channel=False)

            for eachUser in gen_channel.members:
                await game_channel.set_permissions(eachUser, view_channel=True)

        game_inv = await activities.create_activity_invite(game, game_channel.id)
        await gen_channel.send(
            f'<@{interaction.user.id}> has started an activity! Click here to join: https://discord.gg/{game_inv}')
    else:
        await interaction.response.send_message(f'You can only use this in megapod channels, {interaction.user}!',
                                                ephemeral=True)


# Actual Discord bot.
class nmaClient(discord.Client):

    async def setup_hook(self):
        db.poll_db.start()

    async def on_ready(self):
        await tree.sync()
        for guild in client.guilds:
            for channel in guild.channels:
                if channel.name == "command-center":
                    async for message in channel.history(limit=200):
                        await message.delete()
                    msg = await channel.send(embed=interact.send_embed('master'),
                                             view=administrator.CommandDropdownView())
                    await msg.pin()
                elif channel.name == 'verify':
                    async for message in channel.history(limit=200):
                        await message.delete()
                    msg = await channel.send(embed=interact.send_embed('verify'))
                    await msg.pin()
                elif channel.name == 'activity-center':
                    async for message in channel.history(limit=200):
                        await message.delete()
                    msg = await channel.send(embed=interact.send_embed('social'),
                                             view=administrator.SocialDropdownView())
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
            elif message.channel.name == 'verify':
                await message.delete()  # ...Then delete the message.
            elif isinstance(message.channel, discord.DMChannel):  # If the user is DMing the bot...
                await interact.send_embed(message, 'dm')  # ...Send a special message.
            else:  # If the user is neither verifying nor DMing...
                msg_cmd = message.content.split(' ')  # ...Split the message.

                if msg_cmd[0] == '--nma':  # Checking for a command.

                    role = discord.utils.get(message.author.roles, name="Organizer")
                    if role is not None and role.name == 'Organizer':
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
                            id_channels += [discord.utils.get(message.guild.channels, name="lgbtq")]
                        if 'gender' in msg_cmd[2]:
                            id_channels += [discord.utils.get(message.guild.channels, name="gender")]
                        if 'race' in msg_cmd[2]:
                            id_channels += [discord.utils.get(message.guild.channels, name="race")]

                        for eachChan in id_channels:
                            await eachChan.set_permissions(message.author, view_channel=True, send_messages=True)

                        await message.delete()
                    elif msg_cmd[1] == 'auth':
                        await message.channel.send(f"{message.author} auth status: {admin}.")
                    elif msg_cmd[1] == 'podcheck':
                        channel = message.channel.parent
                        members = ''
                        if channel.type == discord.ChannelType.forum:
                            for member in channel.overwrites:
                                if isinstance(member, discord.Member):
                                    if discord.utils.get(message.guild.roles,
                                                         name="Organizer") not in member.roles and discord.utils.get(
                                            message.guild.roles,
                                            name="Staffers") not in member.roles and discord.utils.get(
                                            message.guild.roles, name="Robots") not in member.roles:
                                        if discord.utils.get(message.guild.roles, name="Lead TA") in member.roles:
                                            members = f'{members}{member.name} **(Lead TA)**\n'
                                        elif discord.utils.get(message.guild.roles,
                                                               name="Teaching Assistant") in member.roles:
                                            members = f'{members}{member.name} **(TA)**\n'
                                        else:
                                            members = f'{members}{member.name}\n'
                        elif channel.type == discord.ChannelType.text and '-general' in channel.name:
                            for member in channel.members:
                                if isinstance(member, discord.Member):
                                    if discord.utils.get(message.guild.roles,
                                                         name="Organizer") not in member.roles and discord.utils.get(
                                            message.guild.roles,
                                            name="Staffers") not in member.roles and discord.utils.get(
                                            message.guild.roles, name="Robots") not in member.roles:
                                        if discord.utils.get(message.guild.roles, name="Lead TA") in member.roles:
                                            members = f'{members}{member.name} **(Lead TA)**\n'
                                        elif discord.utils.get(message.guild.roles,
                                                               name="Teaching Assistant") in member.roles:
                                            members = f'{members}{member.name} **(TA)**\n'
                                        else:
                                            members = f'{members}{member.name}\n'
                        await message.channel.send(
                            embed=interact.send_embed('custom', 'Pod Breakdown', f'**Current Members:**\n{members}'))
                    elif msg_cmd[1] == 'getposts' and admin == 1:
                        target_channel = discord.utils.get(message.guild.channels, name=msg_cmd[2])
                        message_dict = []
                        async for eachMessage in target_channel.history(limit=None):
                            message_dict += {
                                'Date': eachMessage.created_at,
                                'Author': eachMessage.author,
                                'Content': eachMessage.content
                            }
                        df = pd.Dataframe(message_dict)
                        df.to_csv(f'{target_channel.name}-log.csv')
                        await message.channel.send(file=discord.File(f'{target_channel.name}-log.csv'))

                    elif msg_cmd[1] == 'timefix' and admin == 1:
                        america_role = discord.utils.get(message.guild.roles, name='americas')
                        eurafrica_role = discord.utils.get(message.guild.roles, name='europe-africa')
                        asia_role = discord.utils.get(message.guild.roles, name='asia-pacific')

                        for eachMember in message.guild.members:
                            try:
                                userInfo = await users.lookup_user(message, eachMember.id)

                                for eachRole in [america_role, eurafrica_role, asia_role]:
                                    if eachRole in eachMember.roles:
                                        await eachMember.remove_roles(eachRole)

                                if userInfo['timeslot'] in ['4', '5']:
                                    time_role = america_role
                                elif userInfo['timeslot'] in ['3']:
                                    time_role = eurafrica_role
                                elif userInfo['timeslot'] in ['1', '2']:
                                    time_role = asia_role

                                await eachMember.add_roles(time_role)
                                await message.channel.send(embed=interact.send_embed('custom', "Time Check",
                                                                                     f"Checked {userInfo['name']}'s time."))
                            except Exception as error:
                                exc_type, exc_obj, exc_tb = sys.exc_info()
                                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                                await message.channel.send(embed=interact.send_embed('custom', "Time Check",
                                                                                     f"{eachMember}, {fname, exc_type, exc_tb.tb_lineno}"))

        # elif message.author == self.user and message.channel.name != 'bot-log' and message.pinned == False:
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
tree = app_commands.CommandTree(client)
tree.add_command(start_activity)


async def delete_channel_after(vc):
    bot_chan = discord.utils.get(vc.guild.channels, name='bot-log')
    await bot_chan.send(
        embed=interact.send_embed('custom', 'Social', f'Voice Channel {vc.name} is empty, deleting after 5 minutes...'))
    print(f'Voice Channel {vc.name} is empty, deleting after 5 minutes...')
    await asyncio.sleep(300)
    vc_still_exists = discord.utils.get(vc.guild.channels, name=vc.name)
    if len(vc.members) == 0 and vc_still_exists:
        await bot_chan.send(embed=interact.send_embed('custom', 'Social', f'Deleting channel {vc.name}'))
        print(f'Deleting channel {vc.name}')
        await vc.delete(reason="Inactive for 5 Minutes")
    elif not vc_still_exists:
        print(f'User deleted channel {vc.name}')


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
