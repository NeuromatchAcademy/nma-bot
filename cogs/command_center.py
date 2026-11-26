import logging

from discord.ext import commands

from utils import administrator, interact

log = logging.getLogger(__name__)


# channel name -> (embed mode, view factory or None)
MENUS = {
    'command-center': ('master', administrator.CommandDropdownView),
    'verify': ('verify', None),
    'activity-center': ('social', administrator.SocialDropdownView),
}


class CommandCenter(commands.Cog):
    """(Re)posts the pinned menus when the bot starts."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ready_once = False

    @commands.Cog.listener()
    async def on_ready(self):
        # on_ready can fire again after a reconnect; the setup below must only run once.
        if self._ready_once:
            return
        self._ready_once = True

        for guild in self.bot.guilds:
            for channel in guild.channels:
                if channel.name in MENUS:
                    mode, view_factory = MENUS[channel.name]
                    await interact.reset_channel(
                        channel, embed=interact.send_embed(mode),
                        view=view_factory() if view_factory else None)
                elif channel.name == 'bot-log':
                    await channel.send(embed=interact.send_embed('restart'))

        log.info("Logged in as %s (%s)", self.bot.user.name, self.bot.user.id)


async def setup(bot: commands.Bot):
    await bot.add_cog(CommandCenter(bot))
