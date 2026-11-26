import json
import re

import discord

from .constants import embed_dict
from .paths import data_path

# (regex searched in the guild name, course name in pods.json); first match wins
GUILD_COURSES = (
    (re.compile(r'Climate'), "Computational Tools for Climate Science"),
    (re.compile(r'(?<![A-Za-z])CN(?![A-Za-z])'), "Computational Neuroscience"),
    (re.compile(r'(?<![A-Za-z])DL(?![A-Za-z])'), "Deep Learning"),
    (re.compile(r'NeuroAI'), "NeuroAI"),
)


def guild_pick(obj):
    """The pod data for the course this guild belongs to, or 'Invalid Course'."""
    with open(data_path('pods.json')) as f:
        db = json.load(f)

    for pattern, course in GUILD_COURSES:
        if pattern.search(obj.guild.name):
            return db[course]
    return 'Invalid Course'


def send_embed(mode, title='None', message='None'):
    if mode != 'custom':
        embed = discord.Embed(title=embed_dict[mode]['title'], description=embed_dict[mode]['description'], color=embed_dict[mode]['color'])

        if 'field' in embed_dict[mode]:
            embed.add_field(name=embed_dict[mode]['field']['name'], value=embed_dict[mode]['field']['value'], inline=False)

    else:
        if 'Administrative' in title:
            color = 0xff8800
        else:
            color = 0x00ff2a
        embed = discord.Embed(title=title, description=message, color=color)

    embed.set_author(name="Neuromatch Bot", url="https://neuromatch.io/", icon_url="https://i.imgur.com/CRoluuv.png")
    return embed


async def reset_channel(channel, *, embed, view=None, pin=True, limit=200):
    """Delete the last `limit` messages in `channel`, then post `embed` (with `view`, pinned if `pin`)."""
    await channel.purge(limit=limit)  # bulk-deletes where Discord allows it
    kwargs = {"embed": embed}
    if view is not None:
        kwargs["view"] = view
    msg = await channel.send(**kwargs)
    if pin:
        await msg.pin()
    return msg
