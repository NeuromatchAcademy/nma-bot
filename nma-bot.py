# -*- coding: utf-8 -*-
"""
Created on Tue May 11 19:57:02 2021

@author: sep27
"""

import gspread
import logging
import discord
import pandas as pd
from discord.ext import commands
from oauth2client.service_account import ServiceAccountCredentials

#Auth
gAuthJson = 'sound-country-274503-cd99a71b16ae.json'
discordToken = 'ODQxOTE5NTU3NDA3ODY2ODkx.YJtwsA.Xt79Ji2xYs9TGY6_PUXJf2QCq2o'

#Google Set-up
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(gAuthJson, scope)
shClient = gspread.authorize(creds)

sheet = shClient.open("CN Pre-pod TAs").sheet1
records_data = sheet.get_all_records()
df = pd.DataFrame.from_dict(records_data)
print(df.head()) #For debugging...

#Logging Set-up
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

staffIndex = [855972293486313529,855972293486313530]
chanDict = {}

def embedGen(title,description,student = None):
    if student != None:
        name = student['name'].split(' ')
        pod = student['pod']
        embed=discord.Embed(title=student['name'], url="https://neuromatch.io/", description=f'Welcome to Neuromatch Academy, {name[0]}!\nYou have been assigned to {pod}.', color=0x109319)
        embed.set_thumbnail(url="https://i.imgur.com/SKdmY9F.png")
        embed.set_footer(text="Need help? You can email support@neuromatch.io or check out our discord tutorial by clicking <here>.")
    else:
        embed=discord.Embed(title=title, url="https://neuromatch.io/", description=description, color=0x109319)
        embed.set_thumbnail(url="https://i.imgur.com/SKdmY9F.png")
        embed.set_footer(text="Need help? You can email support@neuromatch.io or check out our discord tutorial by clicking <here>.")
    return embed

def podFinder(row):
    pod = None
    cursor = 0
    while pod == None:
        cursor += 1
        if sheet.cell(row-cursor,3).value.startswith("GROUP"):
            pod = sheet.cell(row-cursor,2).value
    return f"pod-{pod[4:].lower()}"
            

#Actual Discord bot.
class nmaClient(discord.Client):      
    async def on_ready(self):
        global guild
        global staffRoles
        global allPods
        global logChan
        guild = client.get_guild(855972293472550913)
        staffRoles = []
        staffRoles += [guild.get_role(x) for x in staffIndex]
        logChan = discord.utils.get(guild.channels, name='bot-log')
        allPods = []
        for eachCell in sheet.col_values(2):
            if eachCell.startswith('POD'):
                allPods += [f"pod-{eachCell[4:]}"]
        print('\n==============')
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('==============')

    async def on_message(self, message):
        
        # don't respond to ourselves
        if message.author == self.user:
            return
        
        if not message.guild:
            print(f"\nDM received:\n\"{message.content}\"")
            if "@" in message.content:
                print(f"Student attempting to verify...")
                try:
                    cellInfo = sheet.find(message.content)
                    print(f"Student identified...")
                    studentInfo = {
                        'name' : sheet.cell(cellInfo.row, 4).value,
                        #'type' = sheet.cell(cellInfo.row, ?).value,
                        'pod' : podFinder(cellInfo.row),
                        'id' : sheet.cell(cellInfo.row, 3).value,
                        'email' : sheet.cell(cellInfo.row, cellInfo.row).value,
                        'status' : sheet.cell(cellInfo.row, 6).value,
                        'ta' : sheet.cell(cellInfo.row,7).value,
                        }
                    targUser = guild.get_member(message.author.id)
                    podChan = discord.utils.get(guild.channels, name=studentInfo['pod'])
                    await podChan.set_permissions(targUser, view_channel=True,send_messages=True)
                    if studentInfo['ta'] == 't':
                        for eachChan in [834605904188014634,834599205238472774,834599346782732329,834599233364557855,834605854702960730,834605880746049537]:
                            taChan = guild.get_channel(eachChan)
                            await taChan.set_permissions(targUser, view_channel=True,send_messages=True)
                        await targUser.add_roles(guild.get_role(855972293486313526))
                        await logChan.send(embed=embedGen("User Verified!",f"TA {studentInfo['name']} has successfully verified and can now access the appropriate channels."))
                    else:
                        await logChan.send(embed=embedGen("User Verified!",f"Student {studentInfo['name']} has successfully verified and can now access #{studentInfo['pod']}."))
                    await message.channel.send(embed=embedGen("","", student=studentInfo))
                    print(f"Verification processed.\n")
                except:
                    await message.channel.send(embed=embedGen("Error!","That email does not appear to have been registered...\nPlease contact support@neuromatch.io."))
            else:
                await message.channel.send(embed=embedGen("Error!","Sorry, that didn't work. Please be sure to *only* send your email."))
        
        if message.content.startswith('--nma '):
            
            cmder = guild.get_member(message.author.id)
            
            if any(x in cmder.roles for x in staffRoles) == True:
                
                cmd = message.content[6:]
                
                if cmd.startswith('auth'):
                    await message.channel.send(embed=embedGen("Administrative Message.",f"Authorized user recognized: <@{message.author.id}>."))
                    
                if cmd.startswith('init'):  
                    print('Initializing server...\n')
                    for eachPod in allPods:
                        try:
                            newChan = await guild.create_text_channel(f"{eachPod}")
                            try:    
                                await newChan.set_permissions(guild.default_role, view_channel=False, send_messages=False)
                                for eachRole in staffRoles:
                                    await newChan.set_permissions(eachRole, view_channel=True, send_messages=True)
                            except:
                                print(f"Failed to set {eachPod} permissions.")
                            await logChan.send(embed=embedGen("Administrative Message.",f"Channel creation succeeded for {eachPod}."))
                        except:                            
                            await logChan.send(embed=embedGen("Administrative Message.",f"Channel creation failed for {eachPod}."))
                        
                    print('Server initialization complete.')
                    
                if cmd.startswith('debug'):
                    debugCont = {'Current message channel':message.channel,'chanDict':chanDict,'staffRoles':staffRoles,'allPods':allPods}
                    for allCont in debugCont.keys():
                        try:
                            print(f"{allCont}:\n{debugCont[allCont]}\n")
                        except:
                            print(f"Failed to grab {allCont}\n")
                    await logChan.send(embed=embedGen("Administrative Message.","Debugging requested. Check console log for details."))
                
                if cmd.startswith('quit'):
                    await logChan.send(embed=embedGen("Administrative Message.","Bot shutting down."))
                    quit()
                
            else:
                await message.channel.send(embed=embedGen("Administrative Message.",f"Unauthorized user: <@{message.author.id}>."))

    async def on_member_join(self, member):
        embed=discord.Embed(title="Welcome to the Neuromatch Academy (CN) Discord Server!", url="https://neuromatch.io/", description="In order to sort you into the appropriate channels, please tell me the email address you used to sign up for Neuromatch Academy.", color=0x109319)
        embed.set_thumbnail(url="https://i.imgur.com/SKdmY9F.png")
        embed.set_footer(text="Need help? You can email support@neuromatch.io for assistance or check out our discord tutorial by clicking <here>.")
        await member.send(embed=embed)

#Discord intents -- i.e. ping buckets.
description = "The official NMA Discord Bot."
intents = discord.Intents(messages=True, guilds=True, typing=True, members=True, presences=True)
#bot = commands.Bot(command_prefix='?', description=description, intents=intents)

client = nmaClient(intents=intents)
client.run(discordToken)
activity = discord.Activity(name='Studying brains...', type=discord.ActivityType.watching)
client = discord.Client(activity=activity)