from __future__ import annotations

import secrets
import traceback
from typing import TYPE_CHECKING, Any

import discord
from discord import Intents
from discord.commands import ApplicationContext
from discord.errors import DiscordException
from discord.ext import commands
from discord.ext.commands import errors
from discord.ext.commands.context import Context

from .config import CONFIG
from .logs import BotLogger

if TYPE_CHECKING:
    from .models.modmail import ActiveMail, Ticket


class NhCord(commands.Bot):  # pylint: disable=R0901
    def __init__(self, *args, **options):
        intent = Intents()
        intent.members = True
        intent.guilds = True
        intent.message_content = True
        intent.guild_messages = True
        intent.dm_messages = True
        super().__init__(
            CONFIG["prefix"],
            intents=intent,
            owner_ids=CONFIG["owner_ids"],
            *args,
            **options,
        )
        self.tickets: dict[int, Ticket] = {}
        self.mails: dict[int, ActiveMail] = {}
        self.log = BotLogger("[BOT]")
        self.load_extension(".cogs", package="bot", recursive=False, store=False)
        self.load_extension(".events", package="bot", recursive=False, store=False)

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
        if isinstance(exception, discord.CheckFailure):
            return await context.respond(
                "You cannot perform this action", ephemeral=True
            )
        self.log.critical("An Error Occured!")
        self.log_exc(context, exception)

    async def on_command_error(self, context: Context, exception: errors.CommandError):
        if isinstance(exception, commands.CheckFailure):
            return await context.reply("You cannot perform this action")
        if isinstance(exception, commands.CommandNotFound):
            return await context.reply("Command not found!")
        self.log.critical("An Error Occured!")
        self.log_exc(context, exception)

    async def on_error(self, event_method: str, *args: Any, **kwargs: Any):
        err_id = secrets.token_hex(4).upper()
        self.log.critical("An error occured in %s, id: %s", event_method, err_id)
        with open("./bot/logs/base_exc.log", "a", encoding="utf-8") as excfile:
            excfile.write(f"\n{err_id}\n")
            traceback.print_exc(file=excfile)

    async def on_ready(self):
        await self.change_presence(activity=discord.Game(name="NH: New Era"))
        self.log.info("Logged in as %s", self.user)
        self.log.info("Bot is ready!")
