import discord


def should_handle(bot, message: discord.Message) -> bool:
    """Ignore the bot's own messages, except those deliberately prefixed with `--csrun `."""
    return message.author != bot.user or message.content.startswith("--csrun ")


def is_dm(message: discord.Message) -> bool:
    return isinstance(message.channel, discord.DMChannel)
