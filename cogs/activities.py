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
        self._pending: dict[int, asyncio.Task] = {}  # channel id -> scheduled deletion

    async def cog_unload(self):
        for task in list(self._pending.values()):
            task.cancel()

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
        category = getattr(interaction.channel, 'category', None)
        if category is None or category.name.lower() in PROTECTED_CATEGORIES:
            await interaction.response.send_message(
                f'You can only use this in megapod channels, {interaction.user}!', ephemeral=True)
            return
        game_cat = category
        gen_channel = discord.utils.get(game_cat.channels, name=f'{game_cat.name.lower()}-general')
        if gen_channel is None:
            await interaction.response.send_message(
                f'Could not find #{game_cat.name.lower()}-general in this megapod.', ephemeral=True)
            return
        await interaction.response.send_message(
            f'If this is the first time this command is run in this megapod, this could take a minute. '
            f'Please be patient, {interaction.user}!', ephemeral=True)
        game = activity.value
        game_channel = discord.utils.get(game_cat.channels, name='megapod-games')
        if game_channel is None:
            game_channel = await game_cat.create_voice_channel('megapod-games')
            await game_channel.set_permissions(interaction.guild.default_role, view_channel=False)

            privileged_roles = [role for role in (discord.utils.get(interaction.guild.roles, name=name)
                                                  for name in ("Organizers", "Staffers", "Robots"))
                                if role is not None]
            for user in gen_channel.members:
                if all(role not in user.roles for role in privileged_roles):
                    await game_channel.set_permissions(user, view_channel=True)

        try:
            game_inv = await activities.create_activity_invite(game, game_channel.id)
        except activities.InviteError:
            await interaction.followup.send('Discord would not create the activity invite. Please try again later.',
                                            ephemeral=True)
            return
        await gen_channel.send(
            f'<@{interaction.user.id}> has started an activity! Click here to join: https://discord.gg/{game_inv}')

    async def delete_channel_after(self, vc):
        bot_chan = discord.utils.get(vc.guild.channels, name='bot-log')

        async def notify(text):
            if bot_chan is not None:
                await bot_chan.send(embed=interact.send_embed('custom', 'Social', text))

        message = f'Voice Channel {vc.name} is empty, deleting after 5 minutes...'
        await notify(message)
        log.info(message)
        await asyncio.sleep(EMPTY_CHANNEL_DELAY)
        if discord.utils.get(vc.guild.channels, id=vc.id) is None:
            log.info('User deleted channel %s', vc.name)
            return
        if len(vc.members) == 0:
            await notify(f'Deleting channel {vc.name}')
            log.info('Deleting channel %s', vc.name)
            try:
                await vc.delete(reason="Inactive for 5 Minutes")
            except discord.NotFound:
                log.info('Channel %s was already deleted', vc.name)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        channel = before.channel
        if channel is None or channel.category is None or channel.id in self._pending:
            return
        if (channel.category.name == SOCIAL_CATEGORY and len(channel.members) == 0
                and 'Social Voice Chat' not in channel.name):
            task = self.bot.loop.create_task(self.delete_channel_after(channel))
            self._pending[channel.id] = task  # keep a reference; also dedupes repeat departures
            task.add_done_callback(lambda _t, cid=channel.id: self._pending.pop(cid, None))


async def setup(bot: commands.Bot):
    await bot.add_cog(Activities(bot))
