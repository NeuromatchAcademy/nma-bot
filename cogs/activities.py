import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils import activities, interact
from utils.constants import PROTECTED_CATEGORIES

log = logging.getLogger(__name__)

SOCIAL_CATEGORY = 'social'
EMPTY_CHANNEL_DELAY = 300  # seconds before an empty social voice channel is deleted


class Activities(commands.Cog):
    """Discord embedded activities in megapods, and cleanup of empty social voice channels."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

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
    async def start_activity(self, interaction: discord.Interaction, activity: app_commands.Choice[str]):
        if interaction.channel.category.name.lower() in PROTECTED_CATEGORIES:
            await interaction.response.send_message(
                f'You can only use this in megapod channels, {interaction.user}!', ephemeral=True)
            return
        await interaction.response.send_message(
            f'If this is the first time this command is run in this megapod, this could take a minute. '
            f'Please be patient, {interaction.user}!', ephemeral=True)
        game = activity.value
        game_cat = interaction.channel.category
        game_channel = discord.utils.get(game_cat.channels, name='megapod-games')
        gen_channel = discord.utils.get(game_cat.channels, name=f'{game_cat.name.lower()}-general')
        if game_channel is None:
            game_channel = await game_cat.create_voice_channel('megapod-games')
            await game_channel.set_permissions(interaction.guild.default_role, view_channel=False)

            privileged_roles = [discord.utils.get(interaction.guild.roles, name=name)
                                for name in ("Organizers", "Staffers", "Robots")]
            for user in gen_channel.members:
                if all(role not in user.roles for role in privileged_roles):
                    await game_channel.set_permissions(user, view_channel=True)

        game_inv = await activities.create_activity_invite(game, game_channel.id)
        await gen_channel.send(
            f'<@{interaction.user.id}> has started an activity! Click here to join: https://discord.gg/{game_inv}')

    async def delete_channel_after(self, vc):
        bot_chan = discord.utils.get(vc.guild.channels, name='bot-log')
        await bot_chan.send(embed=interact.send_embed(
            'custom', 'Social', f'Voice Channel {vc.name} is empty, deleting after 5 minutes...'))
        print(f'Voice Channel {vc.name} is empty, deleting after 5 minutes...')
        await asyncio.sleep(EMPTY_CHANNEL_DELAY)
        vc_still_exists = discord.utils.get(vc.guild.channels, name=vc.name)
        if len(vc.members) == 0 and vc_still_exists:
            await bot_chan.send(embed=interact.send_embed('custom', 'Social', f'Deleting channel {vc.name}'))
            print(f'Deleting channel {vc.name}')
            await vc.delete(reason="Inactive for 5 Minutes")
        elif not vc_still_exists:
            print(f'User deleted channel {vc.name}')

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel:
            chan_cat = before.channel.category.name
            if (chan_cat == SOCIAL_CATEGORY and len(before.channel.members) == 0
                    and 'Social Voice Chat' not in before.channel.name):
                self.bot.loop.create_task(self.delete_channel_after(before.channel))


async def setup(bot: commands.Bot):
    await bot.add_cog(Activities(bot))
