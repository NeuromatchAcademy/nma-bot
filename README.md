# NMA Discord Bot
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-4-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->
## Description
The NMA Discord Bot is designed to automate various administrative tasks and interactions within the Neuromatch Academy's Discord Server. Its primary features include server and channel setup, member role assignment, member verification, automated pod handling, and dynamic activity generation and handling.

## Getting Started
To use this bot, you need to have Python installed in your system. Python 3.13.18 is used (managed automatically by [uv](https://docs.astral.sh/uv/), version 0.13.6 or newer).

## Installation
1. Clone the repository: `git clone https://github.com/NeuromatchAcademy/nma-bot`
2. Navigate to the directory: `cd nma-bot`
3. Install the necessary packages: `uv sync`

## Environmental Variables
This bot uses environmental variables stored in a .env file. You need to create this file and store your bot token as follows:
```env
DISCORD_TOKEN=<Your Bot Token>
ADMIN_USER_IDS=<comma-separated Discord user IDs>   # optional
```
Admin buttons are available to members with the `Organizers` role or whose ID is in `ADMIN_USER_IDS`.
**Graduate Server** (destructive) requires the user's ID to be in `ADMIN_USER_IDS`; the role alone is not enough.

## Contest Instructions
If you're forking this repository to participate in the NMA bot contest, here's some guidance to help you navigate the code:

### Project layout
- `nma-bot.py`: entry point. Defines `NmaBot` and lists the cogs to load in `NmaBot.EXTENSIONS`.
- `cogs/`: one discord.py [cog](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html) per feature (`verify`, `members`, `admin_tools`, `activities`, `db_sync`, `command_center`).
- `utils/`: shared logic (database, permissions, embeds, buttons, constants).

### How to add a command.
User-facing commands are Discord slash commands. Put them in a cog under `cogs/`, for example `cogs/hello.py`:

```python
import discord
from discord import app_commands
from discord.ext import commands


class Hello(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(description="Say hello")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Hello, {interaction.user}!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Hello(bot))
```

Then add `"cogs.hello"` to `NmaBot.EXTENSIONS` in `nma-bot.py`. Event handlers work the same way, with `@commands.Cog.listener()`.

Built-in slash commands (in `cogs/members.py`, `cogs/admin_tools.py` and `cogs/activities.py`):

| Command | Who | What it does |
|---|---|---|
| `/identify` | anyone | Grants access to the chosen identity channels (`lgbtq`, `gender`, `race`). |
| `/podcheck` | anyone | Lists the members of the current pod. |
| `/start_activity` | anyone, in megapods | Starts a Discord activity in the megapod. |
| `/getposts channel:` | admins | Exports a channel's history as a CSV file. |
| `/timefix` | admins | Re-syncs time-zone roles from the portal data. |

"Admin" means the `Organizers` role or an ID in `ADMIN_USER_IDS`. The admin commands are also hidden from non-administrators in Discord, but the permission check in the bot is what enforces it.

The old `--nma ...` text commands are gone, and so is `--nma auth`: the **Check Authority** button reports your admin status. Admin actions live in the buttons described below.

### How to add a button.
In `cogs/command_center.py`, the `on_ready` listener sends a message with a special view in the `activity-center` channel. This view is imported from `utils/administrator.py`, and if you look at the `BUTTON_MAPPING` dictionary in that file, you might notice that the dictionary's keys correspond to options in the #activity-center dropdown and the dictionary's values correspond to the buttons and dropdowns the bot loads if the appropriate option is picked in the dropdown. These are defined in `utils/buttons.py` as such:

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

## Testing

The suite is a *characterization* suite: it pins what the bot does today so changes are deliberate.

```bash
uv sync --group dev
uv run pytest                      # run everything (no network, DB or Discord token needed)
uv run pytest --cov=utils --cov=cogs --cov=nma_bot   # with coverage (CI enforces a floor)
uv run pytest --update-snapshots   # accept intentional behaviour changes
```

- Discord objects are replaced by hand-written fakes in `tests/fakes.py`; data files are redirected
  with `NMA_DATA_DIR` (see `utils/paths.py`).
- Golden outputs live in `tests/snapshots/*.json`. A snapshot diff in a PR means behaviour changed:
  review it, then re-run with `--update-snapshots` if it is intended.
- Tests marked `known_bug` assert *currently broken* behaviour on purpose. When you fix one of those
  bugs the test fails; update it to the new, correct behaviour and drop the marker.
- CI (`.github/workflows/ci.yml`) runs ruff and pytest with coverage on every push/PR.

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
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/di1ara"><img src="https://avatars.githubusercontent.com/u/98195964?v=4?s=100" width="100px;" alt="di1ara"/><br /><sub><b>di1ara</b></sub></a><br /><a href="https://github.com/NeuromatchAcademy/nma-bot/commits?author=di1ara" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/iamzoltan"><img src="https://avatars.githubusercontent.com/u/21369773?v=4?s=100" width="100px;" alt="Zoltan"/><br /><sub><b>Zoltan</b></sub></a><br /><a href="https://github.com/NeuromatchAcademy/nma-bot/commits?author=iamzoltan" title="Code">💻</a> <a href="https://github.com/NeuromatchAcademy/nma-bot/commits?author=iamzoltan" title="Tests">⚠️</a> <a href="#infra-iamzoltan" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://www.blueneuron.net"><img src="https://avatars.githubusercontent.com/u/24724403?v=4?s=100" width="100px;" alt="Kevin Rusch"/><br /><sub><b>Kevin Rusch</b></sub></a><br /><a href="https://github.com/NeuromatchAcademy/nma-bot/commits?author=RR-N" title="Code">💻</a> <a href="https://github.com/NeuromatchAcademy/nma-bot/commits?author=RR-N" title="Tests">⚠️</a> <a href="#content-RR-N" title="Content">🖋</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/aslgb"><img src="https://avatars.githubusercontent.com/u/7450056?v=4?s=100" width="100px;" alt="aslgb"/><br /><sub><b>aslgb</b></sub></a><br /><a href="https://github.com/NeuromatchAcademy/nma-bot/commits?author=aslgb" title="Code">💻</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!