# -*- coding: utf-8 -*-
"""
Created on Tue May 11 19:57:02 2021

@author: sep27
"""

from __future__ import print_function
import os.path
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import gspread
import logging
import base64
import discord
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

#Auth
gAuthJson = 'sound-country-274503-cd99a71b16ae.json'
discordToken = 'ODQxOTE5NTU3NDA3ODY2ODkx.YJtwsA.Xt79Ji2xYs9TGY6_PUXJf2QCq2o'

#Google Set-up
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
scopeMail = ['https://www.googleapis.com/auth/gmail.readonly','https://www.googleapis.com/auth/gmail.send','https://www.googleapis.com/auth/gmail.compose','https://mail.google.com/']
creds = ServiceAccountCredentials.from_json_keyfile_name(gAuthJson, scope)
credsMail = None

shClient = gspread.authorize(creds)
sheet = shClient.open("TAsheet").sheet1
records_data = sheet.get_all_records()
df = pd.DataFrame.from_dict(records_data)

if os.path.exists('token.json'):
    credsMail = Credentials.from_authorized_user_file('token.json', scopeMail)
    
if not credsMail or not credsMail.valid:
    if credsMail and credsMail.expired and credsMail.refresh_token:
        credsMail.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', scopeMail)
        credsMail = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.json', 'w') as token:
        token.write(credsMail.to_json())

service = build('gmail', 'v1', credentials=credsMail)
results = service.users().labels().list(userId='me').execute()
labels = results.get('labels', [])

#Logging Set-up
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

staffIndex = [855972293486313529,855972293486313530]
timezoneRoles = {
        'A' : 856931154773803058,
        'B' : 856931206935347200,
        'C' : 856931228993060875,
    }
chanDict = {}

def create_mail(sender, to, subject, message_text):
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes())
    raw = raw.decode()
    return {'raw': raw}

def send_mail(service, user_id, message):
    message = (service.users().messages().send(userId=user_id, body=message)
               .execute())
    print ('Message Id: %s' % message['id'])
    return message

def embedGen(title,description,student = None):
    if student != None:
        name = student['name'].split(' ')
        pod = student['pod']
        embed=discord.Embed(title=student['name'], url="https://neuromatch.io/", description=f'Welcome to Neuromatch Academy, {name[0]}!\nYou have been assigned to {pod}.', color=0x109319)
        embed.set_thumbnail(url="https://i.imgur.com/SKdmY9F.png")
        embed.set_footer(text="Need help? You can email support@neuromatch.io or check out our discord tutorial @ https://youtu.be/7oFfPbitReQ.")
    else:
        embed=discord.Embed(title=title, url="https://neuromatch.io/", description=description, color=0x109319)
        embed.set_thumbnail(url="https://i.imgur.com/SKdmY9F.png")
        embed.set_footer(text="Need help? You can email support@neuromatch.io or check out our discord tutorial @ https://youtu.be/7oFfPbitReQ.")
    return embed            

def rollcallGen(roll):
    finList = ''
    for user in roll:
        finList += f'\n{user}'
    return finList

#Actual Discord bot.
class nmaClient(discord.Client):      
    async def on_ready(self):
        '''global guild
        global staffRoles
        global allPods
        global logChan
        global allMegas
        global podDict
        global masterSheet'''
        
        guild = client.get_guild(855972293472550913)
        
        staffRoles = []
        staffRoles += [guild.get_role(x) for x in staffIndex]
        
        logChan = discord.utils.get(guild.channels, name='bot-log')
        
        masterSheet = pd.DataFrame(sheet.get_all_records())
        print(masterSheet.head())
        
        podDict = {}
        allPods = list(set(masterSheet['pod']))
        allMegas = list(set(masterSheet['megapod']))
        
        for eachMega in allMegas:
            podDict[eachMega] = []
        for eachPod in masterSheet['pod']:
            podDict[df.at[df[df['pod']==eachPod].index.values[0],'megapod']] += [eachPod.replace(" ", "-")]
            
        print('\n==============')
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('==============')

    async def on_message(self, message):
        
        if message.author == self.user:
            return
        
        if not message.guild:
            print(f"\nDM received:\n\"{message.content}\"")
            if "@" in message.content:
                print("Student attempting to verify...")
                try:
                    cellInfo = df[df['email']==message.content].index.values[0]
                    print("Student identified...")
                    studentInfo = {
                        'name' : df.at[cellInfo, 'name'],
                        'pod' : df.at[cellInfo, 'pod'],
                        'role' : df.at[cellInfo, 'role'],
                        'email' : message.content,
                        'megapod' : df.at[cellInfo, 'megapod'],
                        'timezone' : df.at[cellInfo, 'timezone'],
                        }
                    
                    targUser = guild.get_member(message.author.id)
                    await targUser.edit(nick=studentInfo['name'])
                    await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                    if studentInfo['pod'] != 'None':
                        studentInfo['pod'] = studentInfo['pod'].replace(" ", "-")
                        podChan = discord.utils.get(guild.channels, name=studentInfo['pod'])
                        megaGen = discord.utils.get(guild.channels, name=f"{studentInfo['megapod'].replace(' ', '-')}-general")
                        megaTA = discord.utils.get(guild.channels, name=f"{studentInfo['megapod'].replace(' ', '-')}-ta-chat")
                        await targUser.add_roles(guild.get_role(855972293486313525))
                        await megaGen.set_permissions(targUser, view_channel=True,send_messages=True)  
                        await targUser.add_roles(guild.get_role(859309487156625440))
                        await podChan.set_permissions(targUser, view_channel=True,send_messages=True)
                        
                    if studentInfo['role'] == 'leadTA':
                        await targUser.add_roles(guild.get_role(858144978555109387))
                        await targUser.add_roles(guild.get_role(855972293486313526))
                        if studentInfo['pod'] != 'None':
                            await megaTA.set_permissions(targUser, view_channel=True,send_messages=True,manage_messages=True)
                    
                    if studentInfo['role'] == 'TA' or studentInfo['role'] == 'leadTA' or studentInfo['role'] == 'projectTA':
                        for eachChan in ['onboarding','ta-announcements','content-help','pod-dynamics-helpdesk','attendance-helpdesk','finance-helpdesk','lead-ta-discussion','bot-testing']:
                            taChan = discord.utils.get(guild.channels, name=eachChan)
                            await taChan.set_permissions(targUser, view_channel=True,send_messages=True)
                        await targUser.add_roles(guild.get_role(855972293486313526))  
                        if studentInfo['pod'] != 'None':
                            await megaTA.set_permissions(targUser, view_channel=True,send_messages=True,manage_messages=True)
                            await podChan.set_permissions(targUser, view_channel=True,send_messages=True, manage_messages=True)
    
                    if studentInfo['role'] == 'projectTA':
                        await targUser.add_roles(guild.get_role(858748990429855795))
                        for eachChan in ['onboarding','ta-announcements','content-help','pod-dynamics-helpdesk','attendance-helpdesk','finance-helpdesk','lead-ta-discussion','project-ta-discussion','bot-testing']:
                            taChan = discord.utils.get(guild.channels, name=eachChan)
                            await taChan.set_permissions(targUser, view_channel=True,send_messages=True)
                        await targUser.add_roles(guild.get_role(855972293486313526))  
                    
                    await logChan.send(embed=embedGen("User Verified!",f"{studentInfo['role']} {studentInfo['name']} of pod-{studentInfo['pod']} has successfully verified and can now access the appropriate channels."))
                    await message.channel.send(embed=embedGen("","", student=studentInfo))
                    
                    #This bit is for verification confirmation emails.
                    #veriMail = create_mail('discordsupport@neuromatch.io',studentInfo['email'],'Discord Verification Completed.','You have successfully verified your identity on the NMA discord.')
                    #send_mail(service,'me',veriMail)
                
                    print("Verification processed.\n")
                 
                except:
                    await message.channel.send(embed=embedGen("Error!","That email does not appear to have been registered...\nPlease contact support@neuromatch.io or seek help in the #support channel."))
                    await logChan.send(embed=embedGen("WARNING!!",f"{message.author} unsuccessfully tried to verify. Please reach out and investigate."))
            else:
                await message.channel.send(embed=embedGen("Error!","Sorry, that didn't work. Please be sure to *only* send your email."))
        
        #if message.channel == 'support-transcripts':
            #Will be added once matching is finalized.            
        
        if message.content.startswith('--nma '):
            
            cmder = guild.get_member(message.author.id)
            
            if any(x in cmder.roles for x in staffRoles) == True:
                
                cmd = message.content[6:]
                
                if cmd.startswith('auth'):
                    await message.channel.send(embed=embedGen("Administrative Message.",f"Authorized user recognized: <@{message.author.id}>."))
                    
                if cmd.startswith('init'):  
                    print('Initializing server...\n')
                    for eachMega in podDict.keys():
                        await guild.create_category(eachMega)
                        megaCat = discord.utils.get(guild.categories, name=eachMega)
                        
                        newChan = await guild.create_text_channel(f"{eachMega.replace(' ','-')}-general", category=megaCat)
                        await newChan.set_permissions(guild.default_role, view_channel=False, send_messages=False)
                        newChan = await guild.create_text_channel(f"{eachMega.replace(' ','-')}-ta-chat", category=megaCat)
                        await newChan.set_permissions(guild.default_role, view_channel=False, send_messages=False)
                        
                        for eachPod in podDict[eachMega]:
                            try:
                                newChan = await guild.create_text_channel(f"{eachPod}", category=megaCat)
                                await newChan.set_permissions(guild.default_role, view_channel=False, send_messages=False)
                                for eachRole in staffRoles:
                                    await newChan.set_permissions(eachRole, view_channel=True, send_messages=True)
                            except:
                                await logChan.send(embed=embedGen("Administrative Message.",f"Channel creation failed for {eachPod}."))
                                    
                    await logChan.send(embed=embedGen("Administrative Message.",f"SERVER INITIALIZATION COMPLETE."))     
                    print ('Server initialization complete.')
                    
                if cmd.startswith('debug'):
                    debugCont = {'Current message channel':message.channel,'chanDict':chanDict,'staffRoles':staffRoles,'podDict':podDict,'allPods':allPods,'allMegas':allMegas}
                    for allCont in debugCont.keys():
                        try:
                            print(f"{allCont}:\n{debugCont[allCont]}\n")
                        except:
                            print(f"Failed to grab {allCont}\n")
                    await logChan.send(embed=embedGen("Administrative Message.","Debugging requested. Check console log for details."))
                    
                if cmd.startswith('repod'):
                    cmdMsg = cmd.split(' ')
                    targUser = cmdMsg[1]
                    targMail = cmdMsg[2]
                    targPod = cmdMsg[3]
                    
                    try:
                        cellInfo = df[df['email']==targMail].index.values[0]
                        print("Student identified...")
                        studentInfo = {
                            'name' : df.at[cellInfo, 'name'],
                            'pod' : df.at[cellInfo, 'pod'],
                            'role' : df.at[cellInfo, 'role'],
                            'email' : targMail,
                            'megapod' : df.at[cellInfo, 'megapod'],
                            'timezone' : df.at[cellInfo, 'timezone'],
                            }
                        prevTZ = studentInfo['timezone']
                        studentInfo['timezone'] = df.at[df[df['pod']==targPod.replace('-',' ')].index.values[0],'timezone']
                        prevChan = discord.utils.get(guild.channels, name=studentInfo['pod'].replace(' ', '-'))
                        prevMegaGen = discord.utils.get(guild.channels, name=f"{studentInfo['megapod'].replace(' ', '-')}-general")
                        prevMegaTA = discord.utils.get(guild.channels, name=f"{studentInfo['megapod'].replace(' ', '-')}-ta-chat")
                        targUser = discord.utils.get(guild.members,id=int(targUser))
                        podChan = discord.utils.get(guild.channels, name=targPod)
                        megaGen = discord.utils.get(guild.channels, name=f"{df.at[df[df['pod']==targPod.replace('-',' ')].index.values[0],'megapod'].replace(' ', '-')}-general")
                        megaTA = discord.utils.get(guild.channels, name=f"{df.at[df[df['pod']==targPod.replace('-',' ')].index.values[0],'megapod'].replace(' ', '-')}-ta-chat")
                        print(f'targUser = {targUser}\ntargMail = {targMail}\ntargPod = {targPod}\nprevChan = {prevChan}\nprevMegaGen = {prevMegaGen}\nprevMegaTA = {prevMegaTA}\nmegaGen = {megaGen}\nmegaTA = {megaTA}')
                        await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                        await targUser.remove_roles(guild.get_role(timezoneRoles[prevTZ]))
                        await megaGen.set_permissions(targUser, view_channel=True,send_messages=True)
                        await podChan.set_permissions(targUser, view_channel=True,send_messages=True)
                        await prevChan.set_permissions(targUser, view_channel=False,send_messages=False)
                        await prevMegaGen.set_permissions(targUser, view_channel=False,send_messages=False)
                        await prevMegaTA.set_permissions(targUser, view_channel=False,send_messages=False)  
                        await targUser.add_roles(guild.get_role(859309487156625440))
                        
                        if studentInfo['role'] == 'leadTA':
                            await targUser.add_roles(guild.get_role(858144978555109387))
                            await targUser.add_roles(guild.get_role(855972293486313526))
                            await megaTA.set_permissions(targUser, view_channel=True,send_messages=True)
                        
                        if studentInfo['role'] == 'TA' or studentInfo['role'] == 'leadTA':
                            for eachChan in ['onboarding','ta-announcements','content-help','pod-dynamics-helpdesk','attendance-helpdesk','finance-helpdesk','lead-ta-discussion','project-ta-discussion','bot-testing']:
                                taChan = discord.utils.get(guild.channels, name=eachChan)
                                await taChan.set_permissions(targUser, view_channel=True,send_messages=True)
                            await megaTA.set_permissions(targUser, view_channel=True,send_messages=True)
                            await podChan.set_permissions(targUser, view_channel=True,send_messages=True, manage_messages=True)
                            await targUser.add_roles(guild.get_role(855972293486313526))
                        
                        await logChan.send(embed=embedGen("User Repodded!",f"{studentInfo['role']} {studentInfo['name']} has been successfully moved to pod-{studentInfo['pod']} and can now access the appropriate channels."))
                    except:
                        await logChan.send(embed=embedGen("WARNING!","Repodding failed."))
                    
                if cmd.startswith('testmail'):
                    try:
                        testMail = create_mail('discordsupport@neuromatch.io','kevin.rusch@neuromatch.io','Discord Test.','You have successfully sent an email.')
                        send_mail(service,'me',testMail)
                        await message.channel.send(embed=embedGen("Administrative Message.","Test email succeeded."))
                    except:
                        await message.channel.send(embed=embedGen("Administrative Message.","Test email failed."))
                
                if cmd.startswith('podcheck'):
                    try:                
                        rollCall = []
                        for user in message.channel.members:
                            if any(guild.get_role(x) in user.roles for x in [855972293486313530,855972293486313529,855972293472550914]) == True:
                                continue
                            else:
                                if user.nick == None:
                                    rollCall += [user]
                                else:
                                    rollCall += [user.nick]
                        if len(rollCall) == 0:
                            await message.channel.send(embed=embedGen("Administrative Message.",f"Uh-oh. The only people in this channel are administrators, support staff, and robots. If that's wrong, please open a tech ticket in #support."))
                        else:
                            await message.channel.send(embed=embedGen("Pod Rollcall.",f"TA {cmder} requested a rollcall.\nThe following members have verified for this pod:\n{rollcallGen(rollCall)}."))
                    except:
                        await message.channel.send(embed=embedGen("Administrative Message.",f"That didn't work. Please note that this command may only be used in pod channels."))
                
                if cmd.startswith('zoombatch'):
                    zoomies = shClient.open("Zooms").sheet1
                    zoomRecs = zoomies.get_all_records()
                    dZoom = pd.DataFrame.from_dict(zoomRecs)
                    for eachVal in dZoom['pod_name']:
                        zoomLink = dZoom[dZoom['pod_name']==eachVal].index.values[0]
                        zoomLink = dZoom.at[zoomLink, 'zoom_link']
                        podChannel = discord.utils.get(guild.channels, name=eachVal.replace(' ', '-'))
                        zoomRem = await podChannel.send(embed=embedGen("Zoom Reminder",f"The zoom link for {eachVal} is\n{zoomLink}"))
                        await zoomRem.pin()
                        
                if cmd.startswith('leadfix'):
                    for eachMega in allMegas:
                        if eachMega != None or eachMega != 'None':
                            megaLead = "NOT FOUND"
                            megaGen = eachMega.replace(' ', '-')
                            megaGen = discord.utils.get(guild.channels, name=f"{megaGen}-general")
                            for user in megaGen.members:
                                if guild.get_role(858144978555109387) in user.roles:
                                    megaLead = user
                                else:
                                    continue
                            try:
                                for eachPod in podDict[eachMega]:
                                    try:
                                        podChan = discord.utils.get(guild.channels, name=eachPod)
                                        await podChan.set_permissions(megaLead, view_channel=True,send_messages=True) 
                                    except:
                                        await logChan.send(embed=embedGen("Administrative Message.",f"Could not grant Lead TA {megaLead} access to pod-{podChan}."))
                            except:
                                await logChan.send(embed=embedGen("Administrative Message.",f"Error while trying to grant Lead TA {megaLead} access to all pods in the megapod {eachMega}."))
                            await logChan.send(embed=embedGen("Administrative Message.",f"Lead TA {megaLead} now has access to all pods in the megapod {eachMega}."))
                        else:
                            continue
                
                if cmd.startswith('identify'):
                    targUser = cmder
                    queerChan = discord.utils.get(guild.channels, name='lgbtq-in-neuro')
                    genderChan = discord.utils.get(guild.channels, name='gender-in-neuro')
                    raceChan = discord.utils.get(guild.channels, name='race-in-neuro')
                    if 'lgbtq' in cmd:
                        await queerChan.set_permissions(targUser, view_channel=True,send_messages=True)
                        await message.delete()
                    elif 'gender' in cmd:
                        await genderChan.set_permissions(targUser, view_channel=True,send_messages=True)
                        await message.delete()
                    elif 'race' in cmd:
                        await raceChan.set_permissions(targUser, view_channel=True,send_messages=True)
                        await message.delete()
                
                if cmd.startswith('update'):                    
                    try:
                        masterSheet = pd.DataFrame(sheet.get_all_records())
                        print(masterSheet.head())
                        
                        podDict = {}
                        allPods = list(set(masterSheet['pod']))
                        allMegas = list(set(masterSheet['megapod']))
                        
                        for eachMega in allMegas:
                            podDict[eachMega] = []
                        for eachPod in masterSheet['pod']:
                            podDict[df.at[df[df['pod']==eachPod].index.values[0],'megapod']] += [eachPod.replace(" ", "-")]
                        
                        await message.channel.send(embed=embedGen("Administrative Message.",f"Student sheet successfully updated."))
                    except:
                        await message.channel.send(embed=embedGen("Administrative Message.",f"Uh-oh. Something went wrong when tryng to update the sheet."))
                
                if cmd.startswith('quit'):
                    await logChan.send(embed=embedGen("Administrative Message.","Bot shutting down."))
                    quit()
                
            elif any(guild.get_role(x) in cmder.roles for x in [855972293486313526,858144978555109387,858748990429855795]) == True:
                cmd = message.content[6:]
                
                if cmd.startswith('identify'):
                    targUser = cmder
                    queerChan = discord.utils.get(guild.channels, name='lgbtq-in-neuro')
                    genderChan = discord.utils.get(guild.channels, name='gender-in-neuro')
                    raceChan = discord.utils.get(guild.channels, name='race-in-neuro')
                    if 'lgbtq' in cmd:
                        await queerChan.set_permissions(targUser, view_channel=True,send_messages=True)
                        await message.delete()
                    elif 'gender' in cmd:
                        await genderChan.set_permissions(targUser, view_channel=True,send_messages=True)
                        await message.delete()
                    elif 'race' in cmd:
                        await raceChan.set_permissions(targUser, view_channel=True,send_messages=True)
                        await message.delete()
                
                if cmd.startswith('podcheck'):
                    
                    try:                
                        rollCall = []
                        for user in message.channel.members:
                            if any(guild.get_role(x) in user.roles for x in [855972293486313530,855972293486313529,855972293472550914]) == True:
                                continue
                            else:
                                if user.nick == None:
                                    rollCall += [user]
                                else:
                                    rollCall += [user.nick]
                        if len(rollCall) == 0:
                            await message.channel.send(embed=embedGen("Administrative Message.",f"Uh-oh. The only people in this channel are administrators, support staff, and robots. If that's wrong, please open a tech ticket in #support."))
                        else:
                            await message.channel.send(embed=embedGen("Pod Rollcall.",f"TA {cmder} requested a rollcall.\nThe following members have verified for this pod:\n{rollcallGen(rollCall)}."))
                    except:
                        await message.channel.send(embed=embedGen("Administrative Message.",f"That didn't work. Please note that this command may only be used in pod channels."))
            else:     
                cmd = message.content[6:]
                
                if cmd.startswith('identify'):
                    targUser = cmder
                    queerChan = discord.utils.get(guild.channels, name='lgbtq-in-neuro')
                    genderChan = discord.utils.get(guild.channels, name='gender-in-neuro')
                    raceChan = discord.utils.get(guild.channels, name='race-in-neuro')
                    if 'lgbtq' in cmd:
                        await queerChan.set_permissions(targUser, view_channel=True,send_messages=True)
                        await message.delete()
                    elif 'gender' in cmd:
                        await genderChan.set_permissions(targUser, view_channel=True,send_messages=True)
                        await message.delete()
                    elif 'race' in cmd:
                        await raceChan.set_permissions(targUser, view_channel=True,send_messages=True)
                        await message.delete()
                
                else:
                    await message.channel.send(embed=embedGen("Administrative Message.",f"Unauthorized user: <@{message.author.id}>."))

    async def on_member_join(self, member):
        embed=discord.Embed(title="Welcome to the Neuromatch Academy (CN) Discord Server!", url="https://neuromatch.io/", description="In order to sort you into the appropriate channels, please tell me the email address you used to sign up for Neuromatch Academy.", color=0x109319)
        embed.set_thumbnail(url="https://i.imgur.com/SKdmY9F.png")
        embed.set_footer(text="Need help? You can email support@neuromatch.io for assistance or check out our discord tutorial @ https://youtu.be/7oFfPbitReQ.")
        await member.send(embed=embed)

description = "The official NMA Discord Bot."
intents = discord.Intents(messages=True, guilds=True, typing=True, members=True, presences=True)

client = nmaClient(intents=intents)
client.run(discordToken)
activity = discord.Activity(name='Studying brains...', type=discord.ActivityType.watching)
client = discord.Client(activity=activity)