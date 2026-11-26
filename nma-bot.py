import logging
import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

log = logging.getLogger(__name__)

# Auth
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
discordToken = os.getenv("DISCORD_TOKEN")


class NmaBot(commands.Bot):
    # Every feature lives in a cog; add new ones here (see README, "How to add a command").
    EXTENSIONS: tuple[str, ...] = (
        "cogs.verify",
        "cogs.members",
        "cogs.admin_tools",
        "cogs.activities",
        "cogs.db_sync",
        "cogs.command_center",
    )

    async def setup_hook(self):
        for extension in self.EXTENSIONS:
            await self.load_extension(extension)
        await self.tree.sync()  # once per start, not on every gateway reconnect


description = "The official NMA Discord Bot."
intents = discord.Intents(
    messages=True,
    guilds=True,
    members=True,
    reactions=True,
    message_content=True,
    voice_states=True
)

activity = discord.Activity(name="Studying brains...", type=discord.ActivityType.watching)
client = NmaBot(command_prefix=commands.when_mentioned, intents=intents, description=description, activity=activity)
tree = client.tree

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not discordToken:
        raise SystemExit("DISCORD_TOKEN is not set (put it in .env next to nma-bot.py)")
    # log_handler=None: logging is configured above, so discord.py doesn't add a second handler
    client.run(discordToken, log_handler=None)
