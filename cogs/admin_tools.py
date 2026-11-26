import csv
import io
import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils import auth, interact, users
from utils.constants import TIME_ROLE_NAMES, TIMESLOT_ROLES

log = logging.getLogger(__name__)

MAX_REPORTED_FAILURES = 20


def _role(guild, name):
    return discord.utils.get(guild.roles, name=name)


def _embed(title, text):
    return interact.send_embed('custom', title, text)


class AdminTools(commands.Cog):
    """Admin-only slash commands: `/getposts` and `/timefix`."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

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
