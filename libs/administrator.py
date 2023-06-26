import discord
from . import interact, buttons

class CommandDropdownView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(Dropdown())

# Mapping from Dropdown option to Button sets
BUTTON_MAPPING = {
    "Meta Commands": [buttons.CheckAuthority, buttons.CheckUserDetails, buttons.CheckPodDetails, buttons.CleanChannel],
    "Pod Commands": [buttons.AssignUser, buttons.RemoveUser, buttons.RepodUser, buttons.MergePods],
    "Server Commands": [buttons.InitializeServer, buttons.GraduateServer],
}

class Dropdown(discord.ui.Select):
    def __init__(self):

        # Set the options that will be presented inside the dropdown
        options = [
            discord.SelectOption(label='Meta Commands', description='Commands that primarily display information.', emoji='ℹ️'),
            discord.SelectOption(label='Pod Commands', description='Commands that manipulate pod access.', emoji='👥'),
            discord.SelectOption(label='Server Commands', description='Commands that change the server structure.', emoji='⚠️'),
        ]

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(placeholder='Choose which commands to display.', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # Use the interaction object to send a response message containing
        # the user's favourite colour or choice. The self object refers to the
        # Select object, and the values attribute gets a list of the user's
        # selected options. We only want the first one.

        # Create a new View and add buttons to it based on dropdown selection
        view = discord.ui.View()
        for ButtonClass in BUTTON_MAPPING.get(self.values[0], []):
            view.add_item(ButtonClass())

        # Send a message with the created View
        await interaction.response.send_message('', view=view, ephemeral=True)

async def pod_change(message,mode):
    if mode == 'assign':
        print(mode)
    elif mode == 'unassign':
        print(mode)
    elif mode == 'merge':
        print(mode)
    elif mode == 'swap':
        print(mode)
    elif mode == 'identify':
        print(mode)
    else:
        await message.channel.send("Unknown command.")

async def grab(prompt,interaction):
    def vet(m):
        return m.author == interaction.user and m.channel == interaction.channel

    await interaction.response.send_message(prompt, ephemeral=True)
    message = await interaction.client.wait_for('message', check=vet)
    return message


def rollcallGen(roll):
    finList = ""
    for user in roll:
        finList += f"\n{user}"
    return finList