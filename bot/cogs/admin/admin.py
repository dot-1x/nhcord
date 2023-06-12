from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bot.logs.custom_logger import BotLogger
from bot.utils.check import is_admin

from ...exceptions import RequiredPermissionError

if TYPE_CHECKING:
    from bot.bot import NhCord

_log = BotLogger("[ADMIN COG]")


class AdminCog(discord.Cog):
    def __init__(self, bot: NhCord) -> None:
        super().__init__()
        self.bot = bot

    def handle_err_message(
        self, ctx: discord.ApplicationContext | commands.Context, message: str
    ):
        if isinstance(ctx, discord.ApplicationContext):
            self.bot.loop.create_task(ctx.response.send_message(message))
        else:
            self.bot.loop.create_task(ctx.reply(message))

    async def cog_command_error(
        self, ctx: discord.ApplicationContext, error: Exception
    ) -> None:
        if isinstance(error, (discord.CheckFailure, commands.CheckFailure)):
            _log.warning("Check failed invoked by %s", ctx.author)
            return
        raise error

    def cog_check(self, ctx: discord.ApplicationContext | commands.Context):
        if not is_admin(ctx.author):
            return False
        if isinstance(ctx, discord.ApplicationContext):
            if not ctx.guild.me.guild_permissions.manage_roles:
                self.handle_err_message(ctx, "Bot needs a permission to change role!")
                raise RequiredPermissionError
        return True
