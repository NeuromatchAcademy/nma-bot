import asyncio
import logging
import os
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from utils import activities, administrator, db, interact

log = logging.getLogger(__name__)

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
        await interaction.response.send_message(f'If this is the first time this command is run in this megapod, this could take a minute. Please be patient, {interaction.user}!',
                                                ephemeral=True)
        game = activity.value
        game_cat = interaction.channel.category
        game_channel = discord.utils.get(game_cat.channels, name='megapod-games')
        gen_channel = discord.utils.get(game_cat.channels, name=f'{game_cat.name.lower()}-general')
        admin_role = discord.utils.get(interaction.guild.roles, name="Organizers")
        staff_role = discord.utils.get(interaction.guild.roles, name="Staffers")
        robot_role = discord.utils.get(interaction.guild.roles, name="Robots")
        if game_channel is None:
            game_channel = await game_cat.create_voice_channel('megapod-games')
            await game_channel.set_permissions(interaction.guild.default_role, view_channel=False)

            privileged_roles = [admin_role, staff_role, robot_role]

            for user in gen_channel.members:
                if all(role not in user.roles for role in privileged_roles):
                    await game_channel.set_permissions(user, view_channel=True)

        game_inv = await activities.create_activity_invite(game, game_channel.id)
        await gen_channel.send(
            f'<@{interaction.user.id}> has started an activity! Click here to join: https://discord.gg/{game_inv}')
    else:
        await interaction.response.send_message(f'You can only use this in megapod channels, {interaction.user}!',
                                                ephemeral=True)


# Actual Discord bot.
class NmaBot(commands.Bot):
    EXTENSIONS: tuple[str, ...] = ("cogs.verify", "cogs.admin_tools")

    async def setup_hook(self):
        for extension in self.EXTENSIONS:
            await self.load_extension(extension)
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

activity = discord.Activity(name="Studying brains...", type=discord.ActivityType.watching)
client = NmaBot(command_prefix=commands.when_mentioned, intents=intents, description=description, activity=activity)
tree = client.tree
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    client.run(discordToken)
