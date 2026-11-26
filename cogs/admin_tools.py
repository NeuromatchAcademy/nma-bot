import csv
import io
import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils import auth, interact, users
from utils.constants import TIME_ROLE_NAMES, TIMESLOT_ROLES
from utils.members import describe_members

log = logging.getLogger(__name__)

IDENTITY_CHANNELS = ("lgbtq", "gender", "race")
MAX_REPORTED_FAILURES = 20


def _role(guild, name):
    return discord.utils.get(guild.roles, name=name)


def _embed(title, text):
    return interact.send_embed('custom', title, text)


class AdminTools(commands.Cog):
    """Slash commands: `/identify`, `/podcheck`, and (admins only) `/getposts` and `/timefix`."""

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
            embed=_embed('Pod Breakdown', f'**Current Members:**\n{members}'))

    @app_commands.command(description="Export a channel's history as a CSV file (admins only)")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="Channel to archive")
    async def getposts(self, interaction: discord.Interaction,
                       channel: discord.TextChannel | discord.Thread | discord.VoiceChannel):
        if not await auth.require_admin(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            filename = f'{channel.name}-log.csv'
            buffer = io.StringIO(newline='')
            writer = csv.writer(buffer)
            writer.writerow(['Date', 'Author', 'Content'])
            async for each in channel.history(limit=None):
                writer.writerow([each.created_at, each.author, each.content])
            data = io.BytesIO(buffer.getvalue().encode('utf-8'))
            await interaction.followup.send(file=discord.File(data, filename=filename), ephemeral=True)
        except Exception as exc:
            log.exception("Channel archival failed for %s", interaction.user)
            await interaction.followup.send(embed=_embed(
                "Error!", f"{interaction.user}, channel archival failed ({type(exc).__name__}). See the bot logs."),
                ephemeral=True)

    @app_commands.command(description="Re-sync time-zone roles from the portal data (admins only)")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def timefix(self, interaction: discord.Interaction):
        if not await auth.require_admin(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild
        time_roles = {name: _role(guild, name) for name in TIME_ROLE_NAMES}
        approved = _role(guild, 'Approved User')
        checked, failures = 0, []
        for member in guild.members:
            if approved not in member.roles:
                continue
            try:
                info = await users.lookup_user(interaction, member.id)
                keep = time_roles[TIMESLOT_ROLES[info['timeslot']]]
                for role in time_roles.values():
                    if role is not keep and role in member.roles:
                        await member.remove_roles(role)
                if keep not in member.roles:
                    await member.add_roles(keep)
                checked += 1
            except Exception as exc:
                log.exception("Time check failed for %s", member)
                failures.append(f"{member} ({member.id}) failed: {type(exc).__name__}. See the bot logs.")
        lines = [f"Checked the time zone of {checked} member(s)."]
        lines += failures[:MAX_REPORTED_FAILURES]
        if len(failures) > MAX_REPORTED_FAILURES:
            lines.append(f"...and {len(failures) - MAX_REPORTED_FAILURES} more failure(s).")
        await interaction.followup.send(embed=_embed("Time Check", "\n".join(lines)), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminTools(bot))
