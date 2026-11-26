import discord

VERIFY_CHANNEL = "verify"


def should_handle(bot, message: discord.Message) -> bool:
    """Ignore the bot's own messages."""
    return message.author != bot.user


def is_dm(message: discord.Message) -> bool:
    return isinstance(message.channel, discord.DMChannel)
