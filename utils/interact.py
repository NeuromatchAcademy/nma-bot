import discord

game_index = {
    'Watch Together': {
        'max': 0,
        'id': 880218394199220334
    },
    'Poker Night': {
        'max': 25,
        'id': 755827207812677713
    },
    'Betrayal.io': {
        'max': 0,
        'id': 773336526917861400
    },
    'Chess In The Park': {
        'max': 0,
        'id': 832012774040141894
    },
    'Delete Me Calla': {
        'max': 12,
        'id': 832012854282158180
    },
    'Sketch Heads': {
        'max': 16,
        'id': 902271654783242291
    },
    'Letter League': {
        'max': 8,
        'id': 879863686565621790
    },
    'Word Snacks': {
        'max': 8,
        'id': 879863976006127627
    },
    'SpellCast': {
        'max': 100,
        'id': 852509694341283871
    },
    'Checkers In The Park': {
        'max': 0,
        'id': 832013003968348200
    },
    'Blazing 8s': {
        'max': 8,
        'id': 832025144389533716
    },
    'Putt Party': {
        'max': 0,
        'id': 945737671223947305
    },
    'Land-io': {
        'max': 0,
        'id': 903769130790969345
    },
    'Bobble League': {
        'max': 8,
        'id': 947957217959759964
    },
    'Ask Away': {
        'max': 10,
        'id': 976052223358406656
    },
    'Know What I Meme': {
        'max': 9,
        'id': 950505761862189096
    },
    'Bash Out': {
        'max': 16,
        'id': 1006584476094177371
    },
    'Gartic Phone': {
        'max': 16,
        'id': 1007373802981822582
    },
    'Color Together': {
        'max': 100,
        'id': 1039835161136746497
    },
    'Chef Showdown': {
        'max': 15,
        'id': 1037680572660727838
    },
    'Bobble Land: Scrappies': {
        'max': 4,
        'id': 1000100849122553977
    },
    'Jamspace': {
        'max': 0,
        'id': 1070087967294631976
    },
    'Guestbook': {
        'max': 0,
        'id': 1001529884625088563
    },
    'Project K': {
        'max': 0,
        'id': 1011683823555199066
    }
}


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
        'description': "Click on the dropdown below to select a type of command you would like to issue. Buttons will appear that will allow you to go from there.",
        'color': 0x00ff2a
    },
    'social': {
        'title': 'Activity Center',
        'description': 'Click on the dropdown below to select a type of activity you would like to join or start!',
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

async def game_checker(interaction, game, title):

    guild_events = await interaction.guild.fetch_scheduled_events()

    play_cat = discord.utils.get(interaction.guild.channels, name='social')
    play_channel = discord.utils.get(interaction.guild.channels, name=title)

    if play_channel is None:
        play_channel = await interaction.guild.create_voice_channel(name=title, category=play_cat)
    elif len(play_channel.members) < game_index[game]['max'] or game_index[game]['max'] == 0:
        pass
    elif len(play_channel.members) > game_index[game]['max']:
        play_channel = await interaction.guild.create_voice_channel(name=f'{title}-2', category=play_cat)

    print(play_channel.members)

    if len(guild_events) == 0 or all(eachEvent.name != game for eachEvent in guild_events):
        play_event = await interaction.guild.create_scheduled_event(name='Checkers Party',
                                                                    start_time=discord.utils.utcnow(),
                                                                    entity_type=discord.EntityType.voice,
                                                                    channel=play_channel,
                                                                    privacy_level=discord.PrivacyLevel.guild_only,
                                                                    reason=f"{interaction.user} started {game}.")

    play_inv = await play_channel.create_invite(target_application_id=game_index[game]['id'])

    return play_inv
