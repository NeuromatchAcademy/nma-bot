import json
import discord
from .constants import embed_dict


def guild_pick(obj):
    # TODO: set this up in config
    # Is this being used?

    with open('pods.json') as f:
        db = json.load(f)

    if 'Climate' in obj.guild.name:
        return db["Computational Tools for Climate Science"]
    elif 'CN' in obj.guild.name:
        return db["Computational Neuroscience"]
    elif 'DL' in obj.guild.name:
        return db["Deep Learning"]
    else:
        return 'Invalid Course'


def send_embed(mode, title='None', message='None'):
    if mode != 'custom':
        embed = discord.Embed(title=embed_dict[mode]['title'], description=embed_dict[mode]['description'], color=embed_dict[mode]['color'])

        if 'field' in embed_dict[mode].keys():
            embed.add_field(name=embed_dict[mode]['field']['name'], value=embed_dict[mode]['field']['value'], inline=False)

    else:
        if 'Administrative' in title:
            color = 0xff8800
        else:
            color = 0x00ff2a
        embed = discord.Embed(title=title, description=message, color=color)

    embed.set_author(name="Neuromatch Bot", url="https://neuromatch.io/", icon_url="https://i.imgur.com/CRoluuv.png")
    return embed
