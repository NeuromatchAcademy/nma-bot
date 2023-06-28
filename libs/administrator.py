import discord
from . import interact, buttons

class CommandDropdownView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Dropdown(self, 'admin'))


class SocialDropdownView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Dropdown(self, 'social'))

# Mapping from Dropdown option to Button sets
BUTTON_MAPPING = {
    "Meta Commands": [buttons.CheckAuthority, buttons.CheckUserDetails, buttons.CheckPodDetails, buttons.CleanChannel],
    "Pod Commands": [buttons.AssignUser, buttons.RemoveUser, buttons.RepodUser, buttons.MergePods],
    "Server Commands": [buttons.InitializeServer, buttons.GraduateServer],
    "Games": [],
    "Activities": [],
    "Discussions": []
}

class Dropdown(discord.ui.Select):
    def __init__(self, view, mode):

        # Set the options that will be presented inside the dropdown
        if mode == 'admin':
            options = [
                discord.SelectOption(label='Meta Commands', description='Commands that primarily display information.', emoji='ℹ️'),
                discord.SelectOption(label='Pod Commands', description='Commands that manipulate pod access.', emoji='👥'),
                discord.SelectOption(label='Server Commands', description='Commands that change the server structure.', emoji='⚠️'),
            ]
        elif mode == 'social':
            options = [
                discord.SelectOption(label='Games', description='Buttons that start or join games.', emoji='🕹️'),
                discord.SelectOption(label='Activities', description='Activities that don\' quite qualify as games.', emoji='💃'),
                discord.SelectOption(label='Discussions', description='Start a discussion about a topic.', emoji='💬'),
            ]

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(placeholder='Choose which commands to display.', min_values=1, max_values=1, options=options)

        # Save the parent view
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):

        # Clear the items from the parent view
        self.parent_view.clear_items()

        # Add the dropdown back to the parent view
        self.parent_view.add_item(Dropdown(self.parent_view))

        # Create a new View and add buttons to it based on dropdown selection
        for ButtonClass in BUTTON_MAPPING.get(self.values[0], []):
            self.parent_view.add_item(ButtonClass())

        # Update the original message with the new view
        await interaction.response.edit_message(view=self.parent_view)


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