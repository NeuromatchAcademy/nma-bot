# NMA Discord Bot
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-1-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->
## Description
The NMA Discord Bot is designed to automate various administrative tasks and interactions within the Neuromatch Academy's Discord Server. Its primary features include server and channel setup, member role assignment, member verification, automated pod handling, and dynamic activity generation and handling.

## Getting Started
To use this bot, you need to have Python installed in your system. Python 3.8 or higher is recommended. Please also note that you **must** have a discord token for your bot to run. Instructions for how to obtain a token as well as how to invite your bot into a test server are available [here](https://www.writebots.com/discord-bot-token/).

## Installation
1. Clone the repository: `git clone https://github.com/NeuromatchAcademy/nma-bot`
2. Navigate to the directory: `cd nma-bot`
3. Install the necessary packages: `pip install -r requirements.txt`

## Environmental Variables
This bot uses environmental variables stored in a .env file. You need to create this file and store your bot token as follows:
```env
DISCORD_TOKEN=<Your Bot Token>
```

## Contest Instructions
If you're forking this repository to participate in the NMA bot contest, here's some guidance to help you navigate the code:

### How to add a command.
In `nma-bot.py`, under the `on_message` function, you can see that we split incoming messages based on spaces and if the first string in the list is `'--nma'`, we assume that what follows is a command. From there, all you have to do is add an `elif msg_cmd[1] == 'yourcommand'` add add your code underneath. A sample command might thus look like this:

```python
elif msg_cmd[1] == 'samplecommand':
    await message.channel.send(f"Sample command response, {message.author}!")
```

### How to add a button.
In `nma-bot.py`, under the `on_ready` function, you can see that we send a message with a special view in the `activity-center` channel. This view is imported from `utils/administrator.py`, and if you look at the `BUTTON_MAPPING` dictionary in that file, you might notice that the dictionary's keys correspond to options in the #activity-center dropdown and the dictionary's values correspond to the buttons and dropdowns the bot loads if the appropriate option is picked in the dropdown. These are defined in `utils/buttons.py` as such:

```python
class SampleButton(discord.ui.Button):
    def __init__(self, par):
        super().__init__(label='Button Label', style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Sample button response, {interaction.user}!', ephemeral=True)
```

From there, you'd add `buttons.SampleButton` into the appropriate list in the `BUTTON_MAPPING` dictionary in `utils/administrator.py`.

### Key documentation
- [How to get a Discord token](https://www.writebots.com/discord-bot-token/)
- [Discord.py Documentation](https://discordpy.readthedocs.io/en/stable/)
- [Discord.py Support Server](https://discord.gg/r3sSKJJ)
- [Discord.py FAQ](https://discordpy.readthedocs.io/en/stable/faq.html)

## Disclaimer
This bot is designed to be used in Neuromatch Academy course servers and expects a certain server structure as a result. If you server is misconfigured, it will not work for you.

## Licensing

[![CC BY 4.0][cc-by-image]][cc-by]

[![CC BY 4.0][cc-by-shield]][cc-by] [![BSD-3][bsd-3-shield]][bsd-3]

The contents of this repository are shared under under a [Creative Commons Attribution 4.0 International License][cc-by].

Software elements are additionally licensed under the [BSD (3-Clause) License][bsd-3].

Derivative works may use the license that is more appropriate to the relevant context.

[cc-by]: http://creativecommons.org/licenses/by/4.0/
[cc-by-image]: https://i.creativecommons.org/l/by/4.0/88x31.png
[cc-by-shield]: https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg

[bsd-3]: https://opensource.org/licenses/BSD-3-Clause
[bsd-3-shield]: https://camo.githubusercontent.com/9b9ea65d95c9ef878afa1987df65731d47681336/68747470733a2f2f696d672e736869656c64732e696f2f707970692f6c2f736561626f726e2e737667

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="http://www.blueneuron.net"><img src="https://avatars.githubusercontent.com/u/24724403?v=4?s=100" width="100px;" alt="Kevin Rusch"/><br /><sub><b>Kevin Rusch</b></sub></a><br /><a href="https://github.com/NeuromatchAcademy/nma-bot/commits?author=RR-N" title="Code">💻</a> <a href="https://github.com/NeuromatchAcademy/nma-bot/commits?author=RR-N" title="Tests">⚠️</a> <a href="#content-RR-N" title="Content">🖋</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!