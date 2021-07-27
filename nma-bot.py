from __future__ import print_function
import os.path
from email.mime.text import MIMEText
from googleapiclient.discovery import build
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import gspread
import logging
import base64
import discord
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import discord
from discord.ext import commands
import random

#Auth
gAuthJson = 'sound-country-274503-cd99a71b16ae.json'
discordToken = 'ODY4MTI2MDE0MTUxMjE3MTYy.YPrHWg.JorDpdcGFlZhMQeWKXwt5opS-F8'

#Google Set-up
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
scopeMail = ['https://www.googleapis.com/auth/gmail.readonly','https://www.googleapis.com/auth/gmail.send','https://www.googleapis.com/auth/gmail.compose','https://mail.google.com/']
creds = ServiceAccountCredentials.from_json_keyfile_name(gAuthJson, scope)
credsMail = None

shClient = gspread.authorize(creds)
sheet = shClient.open("dlmastersheet").sheet1
records_data = sheet.get_all_records()
df = pd.DataFrame.from_dict(records_data)

projSheet = shClient.open("dlmastersheet").get_worksheet(1)
proj_data = projSheet.get_all_records()
dProj = pd.DataFrame.from_dict(proj_data)

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

staffIndex = [867751492417355836,867751492417355835]
timezoneRoles = {
        'A' : 867751492408573986,
        'B' : 867751492408573985,
        'C' : 867751492408573984,
    }
probDict = {}
chanDict = {}
masterEmb=discord.Embed(title="", url="https://www.neuromatch.io", description="Click on the appropriate reactions below to initiate a bot action. If that doesn't work, you can use the commands listed below as a back-up.", color=0xa400d1)
masterEmb.set_author(name="Administrative Interface", url="https://www.neuromatch.io", icon_url="https://i.imgur.com/NwOh9XV.png")
masterEmb.add_field(name="Reaction-Based Interface", value="To repod a user, click :busts_in_silhouette:.\nTo merge two pods, click :people_hugging:\nTo assign a user to multiple pods, click :zap:.\nTo unassign a user from multiple pods, click :cloud_tornado:.", inline=False)
masterEmb.add_field(name="Pod-Related Commands", value="To repod a user, use `--nma repod <discord-id> <user-email> <new-pod>`.   \nTo merge two pods, use `--nma podmerge <old-pod> <new-pod>`. \nTo assign a user to pods, use `--nma assign <user-id> <pod-n>`.                 \nTo unassign a user from pods, use `--nma unassign <user-id> <pod-n>`.     \nTo check who has verified for a pod, use `--nma podcheck` in the pod channel.", inline=False)
masterEmb.add_field(name="Hotfix Commands", value="To give interactive students access to all public channels, use `--nma unlock`. \nTo grant lead TAs access to all their pods, use `--nma leadfix`. \nTo restore TA access to their pods, use `--nma tafix`.", inline=False)
masterEmb.add_field(name="Debugging Commands", value="To check whether you can use administrative commands, use `--nma auth`.\nTo print all variables to console, use `--nma debug`.", inline=False)

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
        embed.set_thumbnail(url="https://i.imgur.com/hAyp5Vr.png")
        embed.set_footer(text="Need help? You can email support@neuromatch.io or open a ticket in #support.")
    else:
        embed=discord.Embed(title=title, url="https://neuromatch.io/", description=description, color=0x109319)
        #embed.set_thumbnail(url="https://i.imgur.com/hAyp5Vr.png")
        embed.set_footer(text="Need help? You can email support@neuromatch.io or open a ticket in #support.")
    return embed            

def rollcallGen(roll):
    finList = ''
    for user in roll:
        finList += f'\n{user}'
    return finList

#Actual Discord bot.
class nmaClient(discord.Client):      
    async def on_ready(self):
        global guild
        global staffRoles
        global allPods
        global logChan
        global allMegas
        global podDict
        global masterSheet
        global masterChan
        global masterMsg
        global veriChan
        
        guild = client.get_guild(867751492408573982)
        
        staffRoles = []
        staffRoles += [guild.get_role(x) for x in staffIndex]
        
        logChan = discord.utils.get(guild.channels, name='bot-log')
        
        masterChan = discord.utils.get(guild.channels, name='command-center')
        masterMsg = await masterChan.send(embed=masterEmb)
        reactions = ["👥","🫂","🕵️","👀","⚡","🌪️"]
        
        for eachReaction in reactions:
            await masterMsg.add_reaction(eachReaction)
        
        veriChan = discord.utils.get(guild.channels, name='verify')
        
        await veriChan.send(embed=embedGen("Welcome to the Neuromatch Academy DL Server!","To unlock access to all channels, please copy and paste the email address with which you log into the Neuromatch portal into this chat."))
        
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

    async def on_reaction_add(self, reaction, user):
        
        if user == self.user:
            return
        
        cmder = user
        
        reactionMap = {
            "👥" : 'repod', 
            "🫂" : 'podmerge',
            "🕵️" : 'check',
            "👀" : 'podcheck',
            "⚡" : 'assign',
            "🌪️" : 'unassign',
            }
        
        reqVars = {
            'repod' : [['the target user\'s discord ID','user\'s email address','new pod name (formatted a la \'sneaky-pandas\')'],['User:','User\'s Email:','New pod:']],
            'podmerge' : [['the old pod (will be deleted)','the new pod (which everyone will join)'],['Pod to be deleted:','New pod:']],
            'check' : [['the discord ID of the user you want to check'],['User\'s ID:']],
            'podcheck' : [['the name of the pod you want to check (formatted a la \'sneaky-pandas\')'],['Pod to be checked:']],
            'assign' : [['the target user\'s discord ID','any pods you want to add them to (formatted a la \'sneaky-pandas sweet-spiders open-dogs\')'],["User:","Pods to add them to:"]],
            'unassign' : [['the target user\'s discord ID','any pods you want to remove them from (formatted a la \'sneaky-pandas sweet-spiders open-dogs\')'],["User:","Pods to remove them from:"]]
            }
        
        print(str(reaction.message.channel)[:7])
        
        if reaction.message == masterMsg and reaction.message.channel == masterChan:
            
            await masterMsg.remove_reaction(reaction,user)
            
            def check(m):
                return m.author == cmder and m.channel == masterChan
            
            argList = []
            
            if reaction.emoji in reactionMap.keys():
                for eachPrompt in reqVars[reactionMap[reaction.emoji]][0]:
                    lastPrompt = await masterChan.send(embed=embedGen('Administrative Message',f'Please send {eachPrompt}.'))
                    reply = await self.wait_for('message', check=check)
                    argList += [reply.content]
                    await reply.delete()
                    await lastPrompt.delete()
                    
                allLines = []
                for eachItem in range(len(argList)):
                    allLines += [f"**{reqVars[reactionMap[reaction.emoji]][1][eachItem]}** {argList[eachItem]}"]
                
                finStr = "\n".join(allLines)
                lastPrompt = await masterChan.send(embed=embedGen('Administrative Message',f'You want to use the {reactionMap[reaction.emoji]} command with the following details:\n\n{finStr}\n\nTo confirm, reply "Y". To cancel, reply "N".'))
                reply = await self.wait_for('message', check=check)
                procRep = reply.content
                if procRep == 'Y' or procRep == 'y':
                    finCmd = " ".join(argList)
                    cmdMsg = await logChan.send(f'--csrun --nma {reactionMap[reaction.emoji]} {finCmd}')
                    print(cmdMsg.content)
                    await cmdMsg.delete()
                    await logChan.send(f"{user.mention}, command has been executed.")
                    
                elif procRep == 'N' or procRep == 'n':
                    await logChan.send(f"{user.mention}, command has been canceled.")
                else:
                    await logChan.send(f"{user.mention}, invalid response. Command has been canceled.")
                await reply.delete()
                await lastPrompt.delete()
        
        elif reaction.emoji == '🔒' and str(reaction.message.channel)[:7] == 'onboard':
            await reaction.message.channel.delete()
        
    async def on_message(self, message):
        
        if message.author != self.user or message.content.startswith('--csrun '):
            if message.content.startswith('--csrun '):
                message.content = message.content[8:]
                print(f"Bot used the command: {message.content}")
            
            if not message.guild:
                print(f"\nDM received:\n{message.author} said: \"{message.content}\"")
                await message.channel.send(embed=embedGen("Warning!","Hey there.\nIt looks like you tried to send me a direct message. That's no longer support -- instead, please refer to the #verify channel in the NMA server."))     
            
            if message.channel == veriChan: #If the message sent in the verification channel...
                print(message.content)
                if "@" in message.content: #If the message contains an email address...
                    #await message.add_reaction(discord.utils.get(guild.emojis, name=':load:'))
                    #await message.delete() #Delete the message.
                    
                    print("Student attempting to verify...")
                    errCode = 'Email not registered.'
                    errMsg = f'The email in question could not be found.'
                    
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
                        studentInfo['pod'] = studentInfo['pod'].replace(' ', '-')
                        targUser = guild.get_member(message.author.id)
                        await targUser.edit(nick=studentInfo['name'])    
                        if studentInfo['role'] == 'observer':
                            await targUser.add_roles(guild.get_role(867751492417355827))
                        elif studentInfo['role'] == 'student':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                            if studentInfo['pod'] != 'None':
                                podChan = discord.utils.get(guild.channels, name=studentInfo['pod'])
                                megaGen = discord.utils.get(guild.channels, name=f"{studentInfo['megapod'].replace(' ', '-')}-general")
                                await podChan.set_permissions(targUser, view_channel=True,send_messages=True)
                                await megaGen.set_permissions(targUser, view_channel=True,send_messages=True)
                        elif studentInfo['role'] == 'TA':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(867751492417355829))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                            if studentInfo['pod'] != 'None':
                                podChan = discord.utils.get(guild.channels, name=studentInfo['pod'])
                                megaGen = discord.utils.get(guild.channels, name=f"{studentInfo['megapod'].replace(' ', '-')}-general")
                                megaTA = discord.utils.get(guild.channels, name=f"{studentInfo['megapod'].replace(' ', '-')}-ta-chat")
                                await podChan.set_permissions(targUser, view_channel=True,send_messages=True,manage_messages=True)
                                await megaGen.set_permissions(targUser, view_channel=True,send_messages=True)
                                await megaTA.set_permissions(targUser, view_channel=True,send_messages=True)
                        elif studentInfo['role'] == 'leadTA':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(867751492417355829))
                            await targUser.add_roles(guild.get_role(867751492417355830))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                            if studentInfo['pod'] != 'None':
                                podChan = discord.utils.get(guild.channels, name=studentInfo['pod'])
                                megaGen = discord.utils.get(guild.channels, name=f"{studentInfo['megapod'].replace(' ', '-')}-general")
                                megaTA = discord.utils.get(guild.channels, name=f"{studentInfo['megapod'].replace(' ', '-')}-ta-chat")
                                await podChan.set_permissions(targUser, view_channel=True,send_messages=True,manage_messages=True)
                                await megaGen.set_permissions(targUser, view_channel=True,send_messages=True,manage_messages=True)
                                await megaTA.set_permissions(targUser, view_channel=True,send_messages=True,manage_messages=True)
                        elif studentInfo['role'] == 'projectTA':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(867751492417355829))
                            await targUser.add_roles(guild.get_role(867751492417355831))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                        elif studentInfo['role'] == 'consultant':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(868124117067509770))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                        elif studentInfo['role'] == 'mentor':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(867751492417355832))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                        elif studentInfo['role'] == 'speaker':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(867751492417355833))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                        elif studentInfo['role'] == 'sponsor':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(867751492417355834))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                        elif studentInfo['role'] == 'support':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(867751492417355835))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                        else:
                            errCode = 'Invalid Role'
                            errMsg = f"Database suggests that {message.author}'s role is {studentInfo['role']}, but there is no matching discord role."
                            raise ValueError
                        
                        await message.delete() #Delete the message.
                        await logChan.send(embed=embedGen("Administrative Message",f"{message.author} successfully verified.")) #Log the issue.'''
                        
                        #This bit is for verification confirmation emails.
                        #veriMail = create_mail('discordsupport@neuromatch.io',studentInfo['email'],'Discord Verification Completed.','You have successfully verified your identity on the NMA discord.')
                        #send_mail(service,'me',veriMail)
                        
                        print("Verification processed.\n")
                        
                    except: #If something goes wrong during verification...
                        if message.author.id not in probDict.keys:
                            probDict[message.author.id)] = 1
                        else:
                            probDict[message.author.id] += 1
                            if probDict[message.author.id] == 2:
                                await logChan.send(embed=embedGen("Warning!",f"{message.author} has failed to verify twice now. Please investigate.")) #Log the issue.'''
                            elif probDict[message.author.id] > 2:
                                suppRole = guild.get_role(867751492417355835)
                                adminCat = discord.utils.get(guild.categories, name='administrative')
                                newChan = await guild.create_text_channel(f"onboard-ticket-{str(message.author)[:5]}", category=adminCat) #Create a channel dedicated to the mucked-up verification.
                                await newChan.set_permissions(guild.default_role, view_channel=False, send_messages=False) #Set up permissions so the channel is private.
                                await newChan.set_permissions(message.author, view_channel=True, send_messages=True) #Grant the problem user access to the new channel.
                                onbTick = await newChan.send(embed=embedGen(f"{errCode}",f"{errMsg}...\nIf no one assists you within the next two hours, please contact support@neuromatch.io.\nClick the 🔒 reaction to close this ticket.")) #Send an error message.
                                await onbTick.add_reaction('🔒')
                                await logChan.send(embed=embedGen("Warning!",f"{message.author} unsuccessfully tried to verify with the following message:\n{message.content}\nPlease reach out and investigate @ #{newChan}.")) #Log the issue.'''
                                probDict[message.author.id] = -9
                                
                        print("Verification failed.\n")
                        #await message.add_reaction(discord.utils.get(guild.emojis, name='x'))
                        await message.delete() #Delete the message.
                        
                else:
                    await message.delete() #Delete the message.
            
            if message.content.startswith('--nma '): #If the message contains a command...
                
                cmder = guild.get_member(message.author.id) #Grab the discord user trying to use the command.
                cmd = message.content[6:] #Trim the message.
                
                if cmd.startswith('init'): #This command creates channel categories and pod channels for all pods and megapods in the bot's database.
                    print('Initializing server...\n')
                    for eachMega in podDict.keys():
                        podDict[eachMega] = set(podDict[eachMega])
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
                        
                elif cmd.startswith('assign'): #Grants given user access to all pod channels mentioned and their respective megapods.
                    cmdMsg = cmd.split(' ')
                    targUser = discord.utils.get(guild.members,id=int(cmdMsg[1]))
                    for eachPod in cmdMsg:
                        if eachPod != targUser and eachPod != cmdMsg[1] and eachPod != '--nma' and eachPod != 'assign':
                            try:
                                podChan = discord.utils.get(guild.channels, name=eachPod)
                                megaGen = discord.utils.get(guild.channels, name=f"{df.at[df[df['pod']==eachPod.replace('-',' ')].index.values[0],'megapod'].replace(' ', '-')}-general")
                                await megaGen.set_permissions(targUser, view_channel=True,send_messages=True)
                                await podChan.set_permissions(targUser, view_channel=True,send_messages=True)
                                await logChan.send(embed=embedGen("Administrative Message",f"{targUser} was successfully assigned to {eachPod}."))
                            except:
                                await logChan.send(embed=embedGen("WARNING!",f"Could not add {targUser} to pod-{eachPod}."))
                                
                elif cmd.startswith('unassign'): #Removes given user's access to all pod channels mentioned and their respective megapods.
                    cmdMsg = cmd.split(' ')
                    targUser = discord.utils.get(guild.members,id=int(cmdMsg[1]))
                    for eachPod in cmdMsg:
                        if eachPod != targUser and eachPod != '--nma' and eachPod != 'unassign':
                            try:
                                podChan = discord.utils.get(guild.channels, name=eachPod)
                                megaGen = discord.utils.get(guild.channels, name=f"{df.at[df[df['pod']==eachPod.replace('-',' ')].index.values[0],'megapod'].replace(' ', '-')}-general")
                                await megaGen.set_permissions(targUser, view_channel=False,send_messages=False)
                                await podChan.set_permissions(targUser, view_channel=False,send_messages=False)
                                await logChan.send(embed=embedGen("Administrative Message",f"{targUser} was successfully removed from {eachPod}."))
                            except:
                                await logChan.send(embed=embedGen("WARNING!",f"Could not remove {targUser} from pod-{eachPod}."))
                
                elif cmd.startswith('identify'):
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
                
                elif cmd.startswith('auth'): #Debugging command that tells the user whether they are authorized to use administrative commands.
                    await message.channel.send(embed=embedGen("Administrative Message.",f"Authorized user recognized: <@{message.author.id}>."))
            
                elif cmd.startswith('debug'): #Debug command that prints a bunch of variables in the console.
                    debugCont = {'Current message channel':message.channel,'chanDict':chanDict,'staffRoles':staffRoles,'podDict':podDict,'allPods':allPods,'allMegas':allMegas,'podCount':len(allPods)}
                    for allCont in debugCont.keys():
                        try:
                            print(f"{allCont}:\n{debugCont[allCont]}\n")
                        except:
                            print(f"Failed to grab {allCont}\n")
                    await logChan.send(embed=embedGen("Administrative Message.","Debugging requested. Check console log for details."))
                    
                elif cmd.startswith('repod'): #Reassings the given user to the given pod.
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
                        
                        if studentInfo['role'] == 'observer':
                            await targUser.add_roles(guild.get_role(867751492417355827))
                        elif studentInfo['role'] == 'student':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                            if studentInfo['pod'] != 'None':
                                podChan = discord.utils.get(guild.channels, name=studentInfo['pod'])
                                megaGen = discord.utils.get(guild.channels, name=f"{studentInfo['megapod'].replace(' ', '-')}-general")
                                await podChan.set_permissions(targUser, view_channel=True,send_messages=True)
                                await megaGen.set_permissions(targUser, view_channel=True,send_messages=True)
                        elif studentInfo['role'] == 'TA':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(867751492417355829))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                            if studentInfo['pod'] != 'None':
                                podChan = discord.utils.get(guild.channels, name=studentInfo['pod'])
                                megaGen = discord.utils.get(guild.channels, name=f"{studentInfo['megapod'].replace(' ', '-')}-general")
                                megaTA = discord.utils.get(guild.channels, name=f"{studentInfo['megapod'].replace(' ', '-')}-ta-chat")
                                await podChan.set_permissions(targUser, view_channel=True,send_messages=True,manage_messages=True)
                                await megaGen.set_permissions(targUser, view_channel=True,send_messages=True)
                                await megaTA.set_permissions(targUser, view_channel=True,send_messages=True)
                        elif studentInfo['role'] == 'leadTA':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(867751492417355829))
                            await targUser.add_roles(guild.get_role(867751492417355830))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                            if studentInfo['pod'] != 'None':
                                podChan = discord.utils.get(guild.channels, name=studentInfo['pod'])
                                megaGen = discord.utils.get(guild.channels, name=f"{studentInfo['megapod'].replace(' ', '-')}-general")
                                megaTA = discord.utils.get(guild.channels, name=f"{studentInfo['megapod'].replace(' ', '-')}-ta-chat")
                                await podChan.set_permissions(targUser, view_channel=True,send_messages=True,manage_messages=True)
                                await megaGen.set_permissions(targUser, view_channel=True,send_messages=True,manage_messages=True)
                                await megaTA.set_permissions(targUser, view_channel=True,send_messages=True,manage_messages=True)
                        elif studentInfo['role'] == 'projectTA':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(867751492417355829))
                            await targUser.add_roles(guild.get_role(867751492417355831))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                        elif studentInfo['role'] == 'consultant':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(868124117067509770))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                        elif studentInfo['role'] == 'mentor':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(867751492417355832))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                        elif studentInfo['role'] == 'speaker':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(867751492417355833))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                        elif studentInfo['role'] == 'sponsor':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(867751492417355834))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                        elif studentInfo['role'] == 'support':
                            await targUser.add_roles(guild.get_role(867751492417355828))
                            await targUser.add_roles(guild.get_role(867751492417355835))
                            await targUser.add_roles(guild.get_role(timezoneRoles[studentInfo['timezone']]))
                        else:
                            errCode = 'Invalid Role'
                            errMsg = f"Database suggests that {message.author}'s role is {studentInfo['role']}, but there is no matching discord role."
                            raise ValueError
                        
                        await logChan.send(embed=embedGen("User Repodded!",f"{studentInfo['role']} {studentInfo['name']} has been successfully moved to pod-{studentInfo['pod']} and can now access the appropriate channels."))
                    except:
                        await logChan.send(embed=embedGen("WARNING!","Repodding failed."))
                    
                elif cmd.startswith('podmerge'): #Merges the two pods by deleting the first one mentioned and migrating its users to the second one mentioned.
                    cmdMsg = cmd.split(' ')
                    oldPod = discord.utils.get(guild.channels, name=cmdMsg[1])
                    newPod = discord.utils.get(guild.channels, name=cmdMsg[2])          
                    rollCall = []
                    staffCount = 0
                    totalCount = 0
                    for user in oldPod.members:
                        if any(guild.get_role(x) in user.roles for x in [867751492417355836,867751492417355835,867751492408573988]) == True:
                            staffCount += 1
                            continue
                        else:
                            try:
                                await oldPod.set_permissions(user, view_channel=False,send_messages=False)
                                await newPod.set_permissions(user, view_channel=True,send_messages=True)
                                totalCount += 1
                            except:
                                continue
                    await message.channel(embed=embedGen("Administrative Message",f"Successfully moved {totalCount} out of {len(oldPod.members)} users to {cmdMsg[2]}."))
                    if len(oldPod.members) <= staffCount:
                        try:
                            await oldPod.delete()
                        except:
                            await message.channel(embed=embedGen("Administrative Message.",f"Could not delete channel {cmdMsg[1]}."))
                      
                elif cmd.startswith('tafix'): #Grants all teaching assistants access to the appropriate pods should it somehow be lost.
                    for eachChannel in guild.channels:
                        if ' ' in str(eachChannel):
                            continue
                        else:                    
                            for entity, overwrite in eachChannel.overwrites.items():
                                if overwrite.manage_messages:
                                    if str(entity) not in ['@everyone','NMA Staffers','Interactive Student','NMA Organizers','Robots']:
                                        if all(guild.get_role(x) in entity.roles for x in [855972293486313530,855972293486313529,855972293472550914]) == False:
                                            try:
                                                await eachChannel.set_permissions(entity, view_channel=True,send_messages=True,manage_messages=True)
                                                await logChan.send(embed=embedGen("Administrative Message",f"TA {entity} has regained access to pod {eachChannel}."))
                                            except:
                                                await logChan.send(embed=embedGen("Administrative Message",f"Could not grant TA {entity} to pod {eachChannel}."))
                 
                elif cmd.startswith('leadfix'): #Grants all lead TAs access to all the pod channels they supervise.
                    for eachMega in allMegas:
                        if eachMega != None and eachMega != 'None' and eachMega != '':
                            print(eachMega)
                            megaLead = "NOT FOUND"
                            megaGen = eachMega.replace(' ', '-')
                            megaTA = discord.utils.get(guild.channels, name=f"{megaGen}-general")
                            megaGen = discord.utils.get(guild.channels, name=f"{megaGen}-ta-chat")
                            for user in megaGen.members:
                                if guild.get_role(867751492417355830) in user.roles:
                                    megaLead = user
                                else:
                                    continue
                            try:
                                for eachPod in podDict[eachMega]:
                                    try:
                                        podChan = discord.utils.get(guild.channels, name=eachPod)
                                        await podChan.set_permissions(megaLead, view_channel=True,send_messages=True)
                                        await megaTA.set_permissions(megaLead, view_channel=True,send_messages=True) 
                                    except:
                                        await logChan.send(embed=embedGen("Administrative Message.",f"Could not grant Lead TA {megaLead} access to pod-{podChan}."))
                            except:
                                await logChan.send(embed=embedGen("Administrative Message.",f"Error while trying to grant Lead TA {megaLead} access to all pods in the megapod {eachMega}."))
                            await logChan.send(embed=embedGen("Administrative Message.",f"Lead TA {megaLead} now has access to all pods in the megapod {eachMega}."))
                        else:
                            continue    
                        
                elif cmd.startswith('unlock'): #Gives interactive students access to all public channels.
                    for chanCat in [discord.utils.get(guild.categories, id=catID) for catID in [855972294898483226,855972295192477706,855972295192477710]]:
                        for eachChan in chanCat.channels:
                            await eachChan.set_permissions(guild.get_role(855972293486313525), view_channel=True,send_messages=True)
            
                else:
                    await message.channel.send(embed=embedGen("Warning!",f"Command {cmd.split(' ')[0]} does not exist."))
                    
        else:
            return

description = "The official NMA Discord Bot."
intents = discord.Intents(messages=True, guilds=True, typing=True, members=True, presences=True, reactions=True)

client = nmaClient(intents=intents)
client.run(discordToken)
activity = discord.Activity(name='Studying brains...', type=discord.ActivityType.watching)
client = discord.Client(activity=activity)