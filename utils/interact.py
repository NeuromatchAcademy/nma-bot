import discord

embed_dict = {
    'verify': {
        'title': 'Welcome to the course!',
        'description': "To unlock access to all channels, please copy and paste the email address with which you log into the portal into this chat.",
        'color': 0x00ff2a
    },
    'restart': {
        'title': 'Administrative Notice',
        'description': 'The bot has started and is now logged in.',
        'color': 0xff8800
    },
    'master': {
        'title': 'Administrative Interface',
        'description': "Click on the appropriate buttons below to initiate a bot action. If that doesn't work, you can use the commands listed below as a back-up.",
        'color': 0x00ff2a
    },
    'dm': {
        'title': '',
        'description': '',
        'color': 0x00ff2a
    }
}

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