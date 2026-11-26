import re

from discord.ext import commands

from utils import users

from ._common import VERIFY_CHANNEL, is_dm, should_handle

# Deliberately loose: anything shaped like a@b; mentions and chatter are not treated as emails.
EMAIL_RE = re.compile(r'[^@\s<>]+@[^@\s<>]+')


class Verify(commands.Cog):
    """Email verification in the #verify channel."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if not should_handle(self.bot, message) or is_dm(message):
            return
        if message.channel.name != VERIFY_CHANNEL:
            return
        content = message.content.strip()
        if EMAIL_RE.fullmatch(content):  # The user sent an email...
            await users.verify_user(message)  # ...attempt verification...
        await message.delete()  # ...and always delete the message.


async def setup(bot: commands.Bot):
    await bot.add_cog(Verify(bot))
