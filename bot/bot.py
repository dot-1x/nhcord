import json
import secrets
import traceback
from typing import Any, TypedDict

from discord import CheckFailure, Intents
from discord.commands import ApplicationContext
from discord.errors import DiscordException
from discord.ext import commands
from discord.ext.commands import errors
from discord.ext.commands.context import Context

from .logs import BotLogger


class TConfig(TypedDict):
    prefix: str
    owner_ids: list[int]


with open("config.json", "rb") as config_f:
    CONFIG: TConfig = json.load(config_f)


class NhCord(commands.Bot):  # pylint: disable=R0901
    def __init__(self, *args, **options):
        intent = Intents()
        intent.members = True
        intent.guilds = True
        intent.message_content = True
        intent.guild_messages = True
        super().__init__(
            CONFIG["prefix"],
            intents=intent,
            owner_ids=CONFIG["owner_ids"],
            *args,
            **options,
        )
        self.log = BotLogger("[BOT]")
        self.load_extension(".cogs", package="bot", recursive=False, store=False)

    def log_exc(self, ctx: ApplicationContext | Context, exception: Exception):
        err_id = secrets.token_hex(4).upper()
        if isinstance(ctx, ApplicationContext):
            self.loop.create_task(
                ctx.respond(f"An error occured! ID: {err_id}", ephemeral=True)
            )
        else:
            self.loop.create_task(ctx.reply(f"An error occured! ID: {err_id}"))
        with open("./bot/logs/exceptions.log", "a", encoding="utf-8") as excfile:
            excfile.write(f"\n{err_id}\n")
            traceback.print_exception(
                type(exception),
                exception,
                exception.__traceback__,
                file=excfile,
            )

    async def on_application_command_error(
        self, context: ApplicationContext, exception: DiscordException
    ):
        if isinstance(exception, CheckFailure):
            return
        self.log.critical("An Error Occured!")
        self.log_exc(context, exception)

    async def on_command_error(self, context: Context, exception: errors.CommandError):
        if isinstance(exception, CheckFailure):
            return
        self.log.critical("An Error Occured!")
        self.log_exc(context, exception)

    async def on_error(self, event_method: str, *args: Any, **kwargs: Any):
        err_id = secrets.token_hex(4).upper()
        self.log.critical("An error occured in %s, id: %s", event_method, err_id)
        with open("./bot/logs/base_exc.log", "a", encoding="utf-8") as excfile:
            excfile.write(f"\n{err_id}\n")
            traceback.print_exc(file=excfile)

    async def on_ready(self):
        self.log.info("Bot is ready!")
