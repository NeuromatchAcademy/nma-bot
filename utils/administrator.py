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

class CustomView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

# Mapping from Dropdown option to Button sets
BUTTON_MAPPING = {
    "Meta Commands": [buttons.CheckAuthority, buttons.CheckUserDetails, buttons.CheckPodDetails, buttons.CleanChannel],
    "Pod Commands": [buttons.AssignUser, buttons.RemoveUser, buttons.RepodUser, buttons.MergePods],
    "Server Commands": [buttons.InitializeServer, buttons.ForceDB, buttons.GraduateServer],
    "Games": [buttons.GameDropdown],
    "Activities": [buttons.StudyTogether, buttons.CodeTogether, buttons.HangTogether, buttons.WatchTogether],
    "Discussions": [buttons.SampleTopic]
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
            place_h = 'Choose which commands to display.'
        elif mode == 'social':
            options = [
                discord.SelectOption(label='Games', description='Start or join a game!', emoji='🕹️'),
                discord.SelectOption(label='Activities', description='Start or join a study, coding, or hangout group!', emoji='💃'),
                discord.SelectOption(label='Discussions', description='Want to do a deep dive with like-minded students?', emoji='💬'),
            ]
            place_h = 'What would you like to do?'
        # elif mode == 'games':
        #     options = [
        #         discord.SelectOption(label='Checkers', description='Play Checkers!', emoji='🏁'),
        #         discord.SelectOption(label='Minigolf', description='Play minigold with up to 8 players!', emoji='⛳'),
        #         discord.SelectOption(label='Know What I Meme', description='Test your meme knowledge with up to 9 players!', emoji='🤣'),
        #         discord.SelectOption(label='Chess', description='Play Chess!', emoji='♟️'),
        #         discord.SelectOption(label='Gartic Phone', description='Guess each others drawings with up to 16 players!', emoji='☎️'),
        #         discord.SelectOption(label='Bobble League', description='Play virtual soccer with up to 8 players!', emoji='⚽'),
        #         discord.SelectOption(label='Land.io', description='Up to 16 players!', emoji='⚒️'),
        #         discord.SelectOption(label='Sketch Heads', description='Pictionary, with up to 8 players!', emoji='✏️'),
        #         discord.SelectOption(label='Blazing 8s', description='Want to do a deep dive with like-minded students?', emoji='🃏'),
        #         discord.SelectOption(label='SpellCast', description='Do a word search with up to 6 players!', emoji='🤔'),
        #         discord.SelectOption(label='Scrabble', description='Play Scrabble with up to 8 players!', emoji='🅱️'),
        #         discord.SelectOption(label='Poker', description='Play Poker with up to 7 other players!', emoji='♣️'),
        #     ]
        #     place_h = 'Select a game!'

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(placeholder=place_h, min_values=1, max_values=1, options=options)

        # Save the parent view
        self.parent_view = view
        self.mode = mode

    async def callback(self, interaction: discord.Interaction):

        # Clear the items from the parent view
        self.parent_view.clear_items()

        # Add the dropdown back to the parent view
        self.parent_view.add_item(Dropdown(self.parent_view, self.mode))

        # Create a new View and add buttons to it based on dropdown selection
        for ButtonClass in BUTTON_MAPPING.get(self.values[0], []):
            self.parent_view.add_item(ButtonClass(self))

        # Update the original message with the new view
        await interaction.response.edit_message(view=self.parent_view)


def rollcallGen(roll):
    finList = ""
    for user in roll:
        finList += f"\n{user}"
    return finList

