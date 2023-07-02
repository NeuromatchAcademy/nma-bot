import discord
import json
from . import interact, users, db
import re
import subprocess
from datetime import timedelta

game_dict = {
            'Checkers':{
                'max': 0,
                'id': 832013003968348200
            },
            'Minigolf':{
                'max': 0,
                'id': 945737671223947305
            },
            'Know What I Meme':{
                'max': 9,
                'id': 950505761862189096
            },
            'Chess':{
                'max': 0,
                'id': 832012774040141894
            },
            'Gartic Phone':{
                'max': 16,
                'id': 1007373802981822582
            },
            'Bobble League':{
                'max': 8,
                'id': 947957217959759964
            },
            'Land.io':{
                'max': 0,
                'id': 903769130790969345
            },
            'Sketch Heads':{
                'max': 16,
                'id': 902271654783242291
            },
            'Blazing 8s':{
                'max': 8,
                'id': 832025144389533716
            },
            'SpellCast':{
                'max': 100,
                'id': 852509694341283871
            },
            'Scrabble':{
                'max': 8,
                'id': 879863686565621790
            },
            'Poker':{
                'max': 25,
                'id': 755827207812677713
            }
        }

# Load portal data.
with open('pods.json') as f:
    master_db = json.load(f)

class CheckAuthority(discord.ui.Button):
    def __init__(self,par):
        super().__init__(label='Check Authority', style=discord.ButtonStyle.grey)

    async def callback(self, interaction: discord.Interaction):
        role = discord.utils.get(interaction.user.roles, name="NMA Organizers")
        if role is not None and role.name == 'NMA Organizers':
            outcome = 'You do possess administrative powers.'
        else:
            outcome = 'You do not possess administrative powers.'
        await interaction.response.send_message(f'Hey {interaction.user}! {outcome}', ephemeral=True)


class CheckUserDetails(discord.ui.Button):
    def __init__(self,par):
        super().__init__(label='Check User Details', style=discord.ButtonStyle.grey)

    async def callback(self, interaction: discord.Interaction):
        msg = await grab('Tag the user you would like to check.', interaction)

        with open('discord-ids.json') as f:
            id_db = json.load(f)

        target_id = re.sub("[^0-9]", "", msg.content)
        userEmail = id_db[target_id]
        userInfo = await users.lookup_user(msg,target_id)
        await interaction.channel.send(embed=interact.send_embed('custom','User Lookup',f'**Name:** {userInfo["name"]}\n**Email:**: {userEmail}\n**Role:** {userInfo["role"]}\n**Pods:** {userInfo["pods"]}\n**Timezone:** {userInfo["timeslot"]}\n\nInfo requested by {msg.author}.'))
        await msg.delete()


class CheckPodDetails(discord.ui.Button):
    def __init__(self,par):
        super().__init__(label='Check Pod Details', style=discord.ButtonStyle.grey)

    async def callback(self, interaction: discord.Interaction):
        msg = await grab('Paste the name of the pod you want to check.', interaction)
        if ' ' in msg.content:
            target_pod = msg.content.replace(' ', '-')
        else:
            target_pod = msg.content
        channel = discord.utils.get(interaction.guild.channels, name=target_pod)
        members = ''
        for member in channel.members:
            if discord.utils.get(interaction.user.roles,
                                 name="NMA Organizers") not in member.roles and discord.utils.get(
                    interaction.user.roles, name="NMA Staffers") not in member.roles:
                if discord.utils.get(interaction.user.roles, name="Lead TA") in member.roles:
                    members = f'{members}{member.name} **(Lead TA)**\n'
                elif discord.utils.get(interaction.user.roles, name="Teaching Assistant") in member.roles:
                    members = f'{members}{member.name} **(TA)**\n'
                else:
                    members = f'{members}{member.name}\n'
        await interaction.channel.send(embed=interact.send_embed('custom', 'Pod Breakdown', f'**Members:**\n{members}'))
        await msg.delete()


class CleanChannel(discord.ui.Button):
    def __init__(self,par):
        super().__init__(label='Clean Channel', style=discord.ButtonStyle.grey)

    async def callback(self, interaction: discord.Interaction):
        async for message in interaction.channel.history(limit=200):
            await message.delete()
        await interaction.channel.send(embed=interact.send_embed('master'), view=administrator.CommandDropdownView())


class AssignUser(discord.ui.Button):
    def __init__(self,par):
        super().__init__(label='Assign User to Pods', style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        usr = await grab('Paste the ID of the user you want to assign.', interaction)
        target_user = discord.utils.get(interaction.guild.members, name=usr.content)

        msg = await grab('Paste the name of the pod you want to add them to.', interaction)
        if ' ' in msg.content:
            target_pod = msg.content.replace(' ', '-')
        else:
            target_pod = msg.content
        target_channel = discord.utils.get(interaction.guild.channels, name=target_pod)

        await target_channel.set_permissions(target_user, view_channel=True, send_messages=True)
        await interaction.response.send_message(f'Assigned {target_user} to {target_channel}.', ephemeral=True)


class RemoveUser(discord.ui.Button):
    def __init__(self,par):
        super().__init__(label='Remove User from Pods', style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        usr = await grab('Paste the ID of the user you want to unassign.', interaction)
        target_user = discord.utils.get(interaction.guild.members, name=usr.content)

        msg = await grab('Paste the name of the pod you want to remove them from.', interaction)
        if ' ' in msg.content:
            target_pod = msg.content.replace(' ', '-')
        else:
            target_pod = msg.content
        target_channel = discord.utils.get(interaction.guild.channels, name=target_pod)

        await target_channel.set_permissions(target_user, view_channel=False, send_messages=False)
        await interaction.response.send_message(f'Unassigned {target_user} from {target_channel}.', ephemeral=True)


class RepodUser(discord.ui.Button):
    def __init__(self,par):
        super().__init__(label='Repod User', style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        usr = await grab('Paste the ID of the user you want to unassign.', interaction)
        target_user = discord.utils.get(interaction.guild.members, name=usr.content)

        msg = await grab('Paste the name of the pod you want to move them from.', interaction)
        if ' ' in msg.content:
            origin_pod = msg.content.replace(' ', '-')
        else:
            origin_pod = msg.content
        old_channel = discord.utils.get(interaction.guild.channels, name=origin_pod)

        msg = await grab('Paste the name of the pod you want to move them to.', interaction)
        if ' ' in msg.content:
            target_pod = msg.content.replace(' ', '-')
        else:
            target_pod = msg.content
        new_channel = discord.utils.get(interaction.guild.channels, name=target_pod)

        if 'Climate' in message.guild.name:
            nested_dict = master_db["Computational Tools for Climate Science"]
        elif 'CN' in message.guild.name:
            nested_dict = master_db["Computational Neuroscience"]
        elif 'DL' in message.guild.name:
            nested_dict = master_db["Deep Learning"]

        oldInfo = users.find_by_category(nested_dict, origin_pod, 'parent_category')
        newInfo = users.find_by_category(nested_dict, target_pod, 'parent_category')
        old_mega = discord.utils.get(interaction.guild.channels, name=f"{oldInfo['megapod'].replace(' ', '-')}-general")
        new_mega = discord.utils.get(interaction.guild.channels, name=f"{newInfo['megapod'].replace(' ', '-')}-general")

        await old_channel.set_permissions(target_user, view_channel=False, send_messages=False)
        await new_channel.set_permissions(target_user, view_channel=True, send_messages=True)
        await old_mega.set_permissions(target_user, view_channel=False, send_messages=False)
        await new_mega.set_permissions(target_user, view_channel=True, send_messages=True)

        await interaction.response.send_message(f'Repodded {target_user} from {origin_pod} to {target_pod}.',
                                                ephemeral=True)


class MergePods(discord.ui.Button):
    def __init__(self,par):
        super().__init__(label='Merge Pods', style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message('Merging pods', ephemeral=True)


class InitializeServer(discord.ui.Button):
    def __init__(self,par):
        super().__init__(label='Initialize Server', style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=interact.send_embed('custom', 'Administrative Notice', 'Initializing server. This may take a while!'),
            ephemeral=True)
        if 'Climate' in interaction.guild.name:  # Hardcoded, needs to be made future-proof for NMA in a box.
            nested_dict = master_db["Computational Tools for Climate Science"]
        elif 'CN' in interaction.guild.name:
            nested_dict = master_db["Computational Neuroscience"]
        elif 'DL' in interaction.guild.name:
            nested_dict = master_db["Deep Learning"]
        else:
            nested_dict = master_db["Computational Tools for Climate Science"]

        for eachMega in nested_dict['structure']:
            this_cat = await interaction.guild.create_category(eachMega)

            for eachPod in nested_dict['structure'][eachMega]:
                this_pod = await interaction.guild.create_forum(f"{eachPod.replace(' ', '-')}", category=this_cat)
                await this_pod.set_permissions(interaction.guild.default_role, view_channel=False, send_messages=False)
                await this_pod.create_thread(name='Off-Topic',
                                             content='This thread is intended for off-topic discussions.')
                await this_pod.create_thread(name='Coursework',
                                             content='This thread is intended for coursework discussions.')
                await this_pod.create_thread(name='General', content='This thread is intended for general discussions.')

            this_gen = await interaction.guild.create_text_channel(f"{eachMega.replace(' ', '-')}-general",
                                                                   category=this_cat)
            this_ta = await interaction.guild.create_text_channel(f"{eachMega.replace(' ', '-')}-ta-chat",
                                                                  category=this_cat)

            for eachChan in [this_cat, this_gen, this_ta]:
                await eachChan.set_permissions(interaction.guild.default_role, view_channel=False, send_messages=False)


class GraduateServer(discord.ui.Button):
    def __init__(self,par):
        super().__init__(label='Graduate Server', style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user == discord.utils.get(interaction.guild.members, name='blueneuron.net'):
            await interaction.response.send_message(embed=interact.send_embed('custom','Administrative Notice','Graduating server. This may take a while!'), ephemeral=True)
            log_channel = discord.utils.get(interaction.guild.channels, name='bot-log')
            await log_channel.send(embed=interact.send_embed('custom', 'Administrative Notice', f'User {interaction.user} triggered pod purge.'))

            alumnus_role = discord.utils.get(interaction.guild.roles, name='Alumnus')
            ta_alumnus_role = discord.utils.get(interaction.guild.roles, name='TA Alumnus')

            student_role = discord.utils.get(interaction.guild.roles, name='Interactive Student')
            ta_role = discord.utils.get(interaction.guild.roles, name='Teaching Assistant')
            lead_ta_role = discord.utils.get(interaction.guild.roles, name='Lead TA')
            project_ta_role = discord.utils.get(interaction.guild.roles, name='Project TA')
            grad_roles = [student_role, ta_role, lead_ta_role, project_ta_role]
            ta_roles = [ta_role, lead_ta_role, project_ta_role]

            channel_types = [interaction.guild.text_channels, interaction.guild.forums, interaction.guild.voice_channels, interaction.guild.categories]

            for eachType in channel_types:
                for eachObj in eachType:
                    if eachObj.type != discord.ChannelType.category:
                        if eachObj.category.name.lower() not in ['observer track', 'alumni', 'administrative', 'teaching assistants', 'content help',
                                 'projects', 'information', 'lobby', 'professional development', 'social', 'contest',
                                 'diversity']:
                            if eachObj.type != discord.ChannelType.forum:
                                for eachMember in eachObj.members:
                                    if alumnus_role not in eachMember.roles:
                                        await eachMember.add_roles(alumnus_role)
                                        await log_channel.send(embed=interact.send_embed('custom', 'Administrative Notice',
                                                                  f'Assigned alumnus role to {eachMember}.'))
                                    if any(role in eachMember.roles for role in ta_roles):
                                        await eachMember.add_roles(ta_alumnus_role)
                                        await log_channel.send(embed=interact.send_embed('custom', 'Administrative Notice',
                                                                  f'Assigned TA alumnus role to {eachMember}.'))
                                    for eachRole in grad_roles:
                                        if eachRole in eachMember.roles:
                                            await eachMember.remove_roles(eachRole)
                                            await log_channel.send(embed=interact.send_embed('custom','Administrative Notice',f'Removed {eachRole} role from {eachMember}.'))

                            await log_channel.send(embed=interact.send_embed('custom','Administrative Notice',f'Deleted pod {eachObj.name} from megapod {eachObj.category.name}.'))
                            await eachObj.delete()
                    elif eachObj.type == discord.ChannelType.category:
                        if len(eachObj.channels) == 0:
                            await log_channel.send(embed=interact.send_embed('custom','Administrative Notice',f'Deleted megapod {eachObj.name}.'))
                            await eachObj.delete()
            await interaction.channel.send(embed=interact.send_embed('custom','Administrative Notice','Deleted all pod channels and turned everyone into alumni.'))
        else:
            await interaction.response.send_message(embed=interact.send_embed('custom', 'Administrative Notice',
                                                                              f'For security reasons, only Kevin can trigger a pod purge.'),
                                                    ephemeral=True)

class ForceDB(discord.ui.Button):
    def __init__(self,par):
        super().__init__(label='Force Database Update', style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        db.poll_db()

class StudyTogether(discord.ui.Button):
    def __init__(self,par):
        super().__init__(label='Start Study Group', style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'This may take a second. Please be patient, {interaction.user}!', ephemeral=True)
        play_invite = await interact.game_checker(interaction, 'Jamspace', 'study')
        await interaction.channel.send(f'Click here to join the activity: https://discord.gg/{play_invite}')


class CodeTogether(discord.ui.Button):
    def __init__(self,par):
        super().__init__(label='Start Coding Session', style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        play_channel = await interact.game_checker(interaction, 'Jamspace', 'code')

        await interaction.response.send_message('', ephemeral=True)


class HangTogether(discord.ui.Button):
    def __init__(self,par):
        super().__init__(label='Start a Watch Party', style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        play_channel = await interact.game_checker(interaction, 'Watch Together', 'watch-party')

        await interaction.response.send_message('', ephemeral=True)


class HangTogether(discord.ui.Button):
    def __init__(self,par):
        super().__init__(label='Start Hanging Out', style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        play_channel = await interact.game_checker(interaction, 'Jamspace', 'hang')

        await interaction.response.send_message('', ephemeral=True)


class SampleTopic(discord.ui.Button):
    def __init__(self,par):
        super().__init__(label='SampleTopic', style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        play_channel = await interact.game_checker(interaction, 'VC', 'topic')

        await interaction.response.send_message('', ephemeral=True)

class GameDropdown(discord.ui.Select):
    def __init__(self, view):

        # Set the options that will be presented inside the dropdown
        options = [
            discord.SelectOption(label='Checkers', description='Play Checkers!', emoji='🏁'),
            discord.SelectOption(label='Minigolf', description='Play minigold with up to 8 players!', emoji='⛳'),
            discord.SelectOption(label='Know What I Meme', description='Test your meme knowledge with up to 9 players!', emoji='🤣'),
            discord.SelectOption(label='Chess', description='Play Chess!', emoji='♟️'),
            discord.SelectOption(label='Gartic Phone', description='Guess each others drawings with up to 16 players!', emoji='☎️'),
            discord.SelectOption(label='Bobble League', description='Play virtual soccer with up to 8 players!', emoji='⚽'),
            discord.SelectOption(label='Land.io', description='Up to 16 players!', emoji='⚒️'),
            discord.SelectOption(label='Sketch Heads', description='Pictionary, with up to 8 players!', emoji='✏️'),
            discord.SelectOption(label='Blazing 8s', description='Want to do a deep dive with like-minded students?', emoji='🃏'),
            discord.SelectOption(label='SpellCast', description='Do a word search with up to 6 players!', emoji='🤔'),
            discord.SelectOption(label='Scrabble', description='Play Scrabble with up to 8 players!', emoji='🅱️'),
            discord.SelectOption(label='Poker', description='Play Poker with up to 7 other players!', emoji='♣️'),
        ]
        place_h = 'Select a game!'

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(placeholder=place_h, min_values=1, max_values=1, options=options)

        # Save the parent view
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.send_message(f'This may take a second. Please be patient, {interaction.user}!', ephemeral=True)
        play_invite = await interact.game_checker(interaction, 'Jamspace', 'study')
        guild_events = await interaction.guild.fetch_scheduled_events()

        play_cat = discord.utils.get(interaction.guild.channels, name='social')
        play_channel = discord.utils.get(interaction.guild.channels, name=self.values[0])

        if play_channel is None:
            print("Making play channel.")
            play_channel = await interaction.guild.create_voice_channel(name=self.values[0], category=play_cat)
            print(f"Made {play_channel}")
        elif len(play_channel.members) < game_dict[self.values[0]]['max'] or game_dict[self.values[0]]['max'] == 0:
            print("Play channel already exists!")
            pass
        elif len(play_channel.members) > game_dict[self.values[0]]['max']:
            print("Expanding play channels!")
            play_channel = await interaction.guild.create_voice_channel(name=f'{self.values[0]}-2', category=play_cat)

        if len(guild_events) == 0 or all(eachEvent.name != self.values[0] for eachEvent in guild_events):
            play_event = await interaction.guild.create_scheduled_event(name='Checkers Party',
                                                                        start_time=discord.utils.utcnow() + timedelta(
                                                                            seconds=60),
                                                                        entity_type=discord.EntityType.voice,
                                                                        channel=play_channel,
                                                                        privacy_level=discord.PrivacyLevel.guild_only,
                                                                        reason=f"{interaction.user} started {self.values[0]}.")

        subprocess.run(['node', 'bot.js', str(play_channel.id), str(game_dict[self.values[0]]['id'])], check=True)

        with open('invite.txt', 'r') as f:
            play_inv = f.read()

        gaming_channel = discord.utils.get(interaction.guild.channels, name='gaming')
        await gaming_channel.send(f'<@{interaction.user.id}> has started an activity! Click here to join: https://discord.gg/{play_inv}')

async def grab(prompt,interaction):
    def vet(m):
        return m.author == interaction.user and m.channel == interaction.channel

    await interaction.response.send_message(prompt, ephemeral=True)
    message = await interaction.client.wait_for('message', check=vet)
    return message