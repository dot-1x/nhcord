import traceback
from typing import Any
from discord import CheckFailure, Intents
from discord.commands import ApplicationContext
from discord.errors import DiscordException
from discord.ext import commands
from discord.ext.commands import errors
from discord.ext.commands.context import Context

from .logs import BotLogger


class NhCord(commands.Bot):  # pylint: disable=R0901
    def __init__(self, *args, **options):
        intent = Intents()
        intent.members = True
        intent.guilds = True
        intent.message_content = True
        intent.guild_messages = True
        super().__init__(
            ".",
            intents=intent,
            owner_ids=[630659954944114689, 732842920889286687],
            *args,
            **options
        )
        self.log = BotLogger("[BOT]")
        self.load_extension(".cogs", package="bot", recursive=False, store=False)

    def log_exc(self, exception: Exception):
        with open("./bot/logs/exceptions.log", "a", encoding="utf-8") as excfile:
            traceback.print_exception(
                type(exception),
                exception,
                exception.__traceback__,
                file=excfile,
            )

    async def on_application_command_error(
        self, _: ApplicationContext, exception: DiscordException
    ):
        if isinstance(exception, CheckFailure):
            return
        self.log.critical("An Error Occured!")
        self.log_exc(exception)

    async def on_command_error(self, _: Context, exception: errors.CommandError):
        if isinstance(exception, CheckFailure):
            return
        self.log.critical("An Error Occured!")
        self.log_exc(exception)

    async def on_error(self, event_method: str, *args: Any, **kwargs: Any):
        self.log.critical("An error occured in %s", event_method)
        with open("./bot/logs/exceptions.log", "a", encoding="utf-8") as excfile:
            traceback.print_exc(file=excfile)

    async def on_ready(self):
        self.log.info("Bot is ready!")
