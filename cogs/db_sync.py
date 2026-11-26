from discord.ext import commands

from utils import db


class DbSync(commands.Cog):
    """Keeps pods.json in sync with the portal database (polls every minute)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _wait_for_bot(self):
        print('db sync waiting for bot...')
        await self.bot.wait_until_ready()

    async def cog_load(self):
        db.poll_db.before_loop(self._wait_for_bot)
        if not db.poll_db.is_running():
            db.poll_db.start()

    async def cog_unload(self):
        db.poll_db.cancel()


async def setup(bot: commands.Bot):
    await bot.add_cog(DbSync(bot))
