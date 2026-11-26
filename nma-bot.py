import logging
import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils import administrator, interact

log = logging.getLogger(__name__)

# Auth
current_dir = Path(__file__).resolve().parent
# parent_dir = current_dir.parent
env_file_path = current_dir / ".env"
load_dotenv(dotenv_path=env_file_path)

discordToken = os.getenv("DISCORD_TOKEN")


# Actual Discord bot.
class NmaBot(commands.Bot):
    EXTENSIONS: tuple[str, ...] = ("cogs.verify", "cogs.admin_tools", "cogs.activities", "cogs.db_sync")

    async def setup_hook(self):
        for extension in self.EXTENSIONS:
            await self.load_extension(extension)

    async def on_ready(self):
        await tree.sync()
        for guild in client.guilds:
            for channel in guild.channels:
                if channel.name == "command-center":
                    async for message in channel.history(limit=200):
                        await message.delete()
                    msg = await channel.send(embed=interact.send_embed('master'),
                                             view=administrator.CommandDropdownView())
                    await msg.pin()
                elif channel.name == 'verify':
                    async for message in channel.history(limit=200):
                        await message.delete()
                    msg = await channel.send(embed=interact.send_embed('verify'))
                    await msg.pin()
                elif channel.name == 'activity-center':
                    async for message in channel.history(limit=200):
                        await message.delete()
                    msg = await channel.send(embed=interact.send_embed('social'),
                                             view=administrator.SocialDropdownView())
                    await msg.pin()
                elif channel.name == 'bot-log':
                    await channel.send(embed=interact.send_embed('restart'))

        print("\n==============")
        print("Logged in as")
        print(self.user.name)
        print(self.user.id)
        print("==============")


description = "The official NMA Discord Bot."
intents = discord.Intents(
    messages=True,
    guilds=True,
    typing=True,
    members=True,
    presences=True,
    reactions=True,
    message_content=True,
    voice_states=True
)

activity = discord.Activity(name="Studying brains...", type=discord.ActivityType.watching)
client = NmaBot(command_prefix=commands.when_mentioned, intents=intents, description=description, activity=activity)
tree = client.tree


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    client.run(discordToken)
