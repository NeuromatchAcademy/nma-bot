import csv
import io
import logging
import re

import discord
from discord.ext import commands

from utils import auth, interact, users
from utils.constants import TIME_ROLE_NAMES, TIMESLOT_ROLES
from utils.members import describe_members

from ._common import VERIFY_CHANNEL, is_dm, should_handle

log = logging.getLogger(__name__)

PREFIX = "--nma"


def _role(guild, name):
    return discord.utils.get(guild.roles, name=name)


class AdminTools(commands.Cog):
    """Text commands: `--nma identify|auth|podcheck|getposts|timefix`."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # name -> (handler, needs_admin, minimum number of words after the prefix)
        self.handlers = {
            'identify': (self.identify, False, 2),
            'auth': (self.auth, False, 1),
            'podcheck': (self.podcheck, False, 1),
            'getposts': (self.getposts, True, 2),
            'timefix': (self.timefix, True, 1),
        }

    @commands.Cog.listener()
    async def on_message(self, message):
        if not should_handle(self.bot, message) or is_dm(message):
            return
        if message.channel.name == VERIFY_CHANNEL:  # handled by the verify cog
            return
        words = message.content.split(' ')
        if words[0] != PREFIX or len(words) < 2:
            return
        entry = self.handlers.get(words[1])
        if entry is None:
            return
        handler, needs_admin, min_words = entry
        is_admin = auth.is_admin(message.author)
        if (needs_admin and not is_admin) or len(words) < min_words + 1:
            return
        await handler(message, words, 1 if is_admin else 0)

    async def identify(self, message, words, admin):
        wanted = [name for name in ("lgbtq", "gender", "race") if name in words[2]]
        for name in wanted:
            channel = discord.utils.get(message.guild.channels, name=name)
            if channel is None:
                log.warning("identify: no #%s channel in %s", name, message.guild)
                continue
            await channel.set_permissions(message.author, view_channel=True, send_messages=True)
        await message.delete()

    async def auth(self, message, words, admin):
        await message.channel.send(f"{message.author} auth status: {admin}.")

    async def podcheck(self, message, words, admin):
        # In a thread, inspect the parent channel; elsewhere, the channel itself.
        channel = getattr(message.channel, 'parent', None) or message.channel
        members = ''
        if channel.type == discord.ChannelType.forum:
            members = describe_members(message.guild, channel.overwrites)
        elif channel.type == discord.ChannelType.text and '-general' in channel.name:
            members = describe_members(message.guild, channel.members)
        await message.channel.send(
            embed=interact.send_embed('custom', 'Pod Breakdown', f'**Current Members:**\n{members}'))

    async def getposts(self, message, words, admin):
        await message.channel.send(embed=interact.send_embed(
            'custom', 'Administrative Notice', 'Starting channel archival -- this might take a while!'))

        try:
            if '#' in words[2]:
                target_id = int(re.sub("[^0-9]", "", words[2]))
                target_channel = discord.utils.get(message.guild.channels, id=target_id)
            else:
                target_channel = discord.utils.get(message.guild.channels, name=words[2])
            if target_channel is None:
                raise LookupError(f"no channel matches {words[2]!r}")

            filename = f'{target_channel.name}-log.csv'
            buffer = io.StringIO(newline='')
            writer = csv.writer(buffer)
            writer.writerow(['Date', 'Author', 'Content'])
            async for each in target_channel.history(limit=None):
                writer.writerow([each.created_at, each.author, each.content])
            data = io.BytesIO(buffer.getvalue().encode('utf-8'))
            await message.channel.send(file=discord.File(data, filename=filename))
        except Exception as exc:
            log.exception("Channel archival failed for %s", message.author)
            await message.channel.send(embed=interact.send_embed(
                'custom', "Error!",
                f"{message.author}, channel archival failed ({type(exc).__name__}). See the bot logs."))

    async def timefix(self, message, words, admin):
        guild = message.guild
        time_roles = {name: _role(guild, name) for name in TIME_ROLE_NAMES}
        approved = _role(guild, 'Approved User')
        checked = 0
        for member in guild.members:
            if approved not in member.roles:
                continue
            try:
                info = await users.lookup_user(message, member.id)
                keep = time_roles[TIMESLOT_ROLES[info['timeslot']]]
                for role in time_roles.values():
                    if role is not keep and role in member.roles:
                        await member.remove_roles(role)
                if keep not in member.roles:
                    await member.add_roles(keep)
                checked += 1
            except Exception as exc:
                log.exception("Time check failed for %s", member)
                await message.channel.send(embed=interact.send_embed(
                    'custom', "Time Check", f"{member} ({member.id}) failed: {type(exc).__name__}. See the bot logs."))
        await message.channel.send(embed=interact.send_embed(
            'custom', "Time Check", f"Checked the time zone of {checked} member(s)."))


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminTools(bot))
