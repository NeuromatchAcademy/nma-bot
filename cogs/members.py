import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils import interact
from utils.members import describe_members

log = logging.getLogger(__name__)

IDENTITY_CHANNELS = ("lgbtq", "gender", "race")


class Members(commands.Cog):
    """Slash commands for everyone: `/identify` and `/podcheck`."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(description="Get access to the identity channels you choose")
    @app_commands.guild_only()
    @app_commands.describe(lgbtq="LGBTQ+ channel", gender="Gender channel", race="Race channel")
    async def identify(self, interaction: discord.Interaction,
                       lgbtq: bool = False, gender: bool = False, race: bool = False):
        chosen = [name for name, wanted in zip(IDENTITY_CHANNELS, (lgbtq, gender, race)) if wanted]
        if not chosen:
            await interaction.response.send_message("Choose at least one channel.", ephemeral=True)
            return
        granted, missing = [], []
        for name in chosen:
            channel = discord.utils.get(interaction.guild.channels, name=name)
            if channel is None:
                log.warning("identify: no #%s channel in %s", name, interaction.guild)
                missing.append(name)
                continue
            await channel.set_permissions(interaction.user, view_channel=True, send_messages=True)
            granted.append(name)
        text = f"Access granted: {', '.join(granted) or 'none'}."
        if missing:
            text += f" Not available on this server: {', '.join(missing)}."
        await interaction.response.send_message(text, ephemeral=True)

    @app_commands.command(description="List the members of this pod")
    @app_commands.guild_only()
    async def podcheck(self, interaction: discord.Interaction):
        # In a thread, inspect the parent channel; elsewhere, the channel itself.
        channel = getattr(interaction.channel, 'parent', None) or interaction.channel
        members = ''
        if channel.type == discord.ChannelType.forum:
            members = describe_members(interaction.guild, channel.overwrites)
        elif channel.type == discord.ChannelType.text and '-general' in channel.name:
            members = describe_members(interaction.guild, channel.members)
        await interaction.response.send_message(
            embed=interact.send_embed('custom', 'Pod Breakdown', f'**Current Members:**\n{members}'))


async def setup(bot: commands.Bot):
    await bot.add_cog(Members(bot))
