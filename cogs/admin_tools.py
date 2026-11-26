import logging
import re

import discord
import pandas as pd
from discord.ext import commands

from utils import interact, users

from ._common import is_dm, should_handle

log = logging.getLogger(__name__)

PREFIX = "--nma"
VERIFY_CHANNEL = "verify"


def _role(guild, name):
    return discord.utils.get(guild.roles, name=name)


def describe_members(guild, members) -> str:
    """One line per non-staff member, labelled (Lead TA) / (TA) where applicable."""
    staff = [_role(guild, "Organizers"), _role(guild, "Staffers"), _role(guild, "Robots")]
    lead_ta, ta = _role(guild, "Lead TA"), _role(guild, "Teaching Assistant")
    lines = ''
    for member in members:
        if not isinstance(member, discord.Member) or any(r in member.roles for r in staff):
            continue
        if lead_ta in member.roles:
            lines += f'{member.name} **(Lead TA)**\n'
        elif ta in member.roles:
            lines += f'{member.name} **(TA)**\n'
        else:
            lines += f'{member.name}\n'
    return lines


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
        is_admin = discord.utils.get(message.author.roles, name="Organizers") is not None
        if (needs_admin and not is_admin) or len(words) < min_words + 1:
            return
        await handler(message, words, 1 if is_admin else 0)

    async def identify(self, message, words, admin):
        wanted = [name for name in ("lgbtq", "gender", "race") if name in words[2]]
        for name in wanted:
            channel = discord.utils.get(message.guild.channels, name=name)
            await channel.set_permissions(message.author, view_channel=True, send_messages=True)
        await message.delete()

    async def auth(self, message, words, admin):
        await message.channel.send(f"{message.author} auth status: {admin}.")

    async def podcheck(self, message, words, admin):
        channel = message.channel.parent
        members = ''
        if channel.type == discord.ChannelType.forum:
            members = describe_members(message.guild, channel.overwrites)
        elif channel.type == discord.ChannelType.text and '-general' in channel.name:
            members = describe_members(message.guild, channel.members)
        await message.channel.send(
            embed=interact.send_embed('custom', 'Pod Breakdown', f'**Current Members:**\n{members}'))

    async def getposts(self, message, words, admin):
        if '#' in words[2]:
            target_id = int(re.sub("[^0-9]", "", words[2]))
            target_channel = discord.utils.get(message.guild.channels, id=target_id)
        else:
            target_channel = discord.utils.get(message.guild.channels, name=words[2])

        await message.channel.send(embed=interact.send_embed(
            'custom', 'Administrative Notice', 'Starting channel archival -- this might take a while!'))

        try:
            rows = []
            async for each in target_channel.history(limit=None):
                rows.append({'Date': each.created_at, 'Author': each.author, 'Content': each.content})
            filename = f'{target_channel.name}-log.csv'
            pd.DataFrame(rows).to_csv(filename)
            await message.channel.send(file=discord.File(filename))
        except Exception as exc:
            log.exception("Channel archival failed for %s", message.author)
            await message.channel.send(embed=interact.send_embed(
                'custom', "Error!",
                f"{message.author}, channel archival failed ({type(exc).__name__}). See the bot logs."))

    async def timefix(self, message, words, admin):
        guild = message.guild
        americas, eurafrica = _role(guild, 'americas'), _role(guild, 'europe-africa')
        asia = _role(guild, 'asia-pacific')
        approved = _role(guild, 'Approved User')
        # timeslot -> (roles to remove, role to add)
        role_mappings = {
            '4': ([eurafrica, asia], americas),
            '5': ([eurafrica, asia], americas),
            '3': ([americas, asia], eurafrica),
            '1': ([eurafrica, americas], asia),
            '2': ([eurafrica, americas], asia),
        }
        for member in guild.members:
            if approved not in member.roles:
                continue
            try:
                info = await users.lookup_user(message, member.id)
                to_remove, time_role = role_mappings[info['timeslot']]
                for role in to_remove:
                    if role in member.roles:
                        await member.remove_roles(role)
                await member.add_roles(time_role)
                await message.channel.send(embed=interact.send_embed(
                    'custom', "Time Check", f"Checked {info['name']}'s time."))
            except Exception as exc:
                log.exception("Time check failed for %s", member)
                await message.channel.send(embed=interact.send_embed(
                    'custom', "Time Check", f"{member} ({member.id}) failed: {type(exc).__name__}. See the bot logs."))


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminTools(bot))
