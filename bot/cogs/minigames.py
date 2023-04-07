from __future__ import annotations
import asyncio
import json
from random import shuffle

from typing import TYPE_CHECKING, Dict, List
from discord import (
    ApplicationContext,
    CheckFailure,
    Cog,
    Colour,
    Embed,
    Message,
    Role,
    SlashCommandGroup,
    option,
    slash_command,
    Member,
)
from discord.ext.commands import Context

from ..models.minigames.minigames_models import (
    RunningGame,
    BridgeGameView,
    GLASS_GAME_FORMATTER,
)
from ..data.minigames import BridgeGameSettings

if TYPE_CHECKING:
    from ..bot import NhCord

__all__ = ("MinigamesCog",)


class MinigamesCog(Cog):
    mg_game = SlashCommandGroup("mg", "Main commands for minigames related")

    def __init__(self, bot: NhCord) -> None:
        self.bot = bot
        with open(
            "bot/data/minigames/minigames_settings.json", "r", encoding="utf-8"
        ) as settings:
            setting = json.load(settings)
            self.authorized: List[int] = setting["auth_command"]
        self.running_game: Dict[int, RunningGame] = {}

    async def handle_err_message(self, ctx: ApplicationContext | Context, message: str):
        if isinstance(ctx, ApplicationContext):
            await ctx.response.send_message(message, ephemeral=True)
        else:
            await ctx.reply(message)

    async def cog_command_error(
        self, ctx: ApplicationContext, error: Exception
    ) -> None:
        if isinstance(error, CheckFailure):
            self.bot.log.warning(f"Check failed invoked by {ctx.author}")
        else:
            raise error

    def cog_check(self, ctx: ApplicationContext | Context):
        if ctx.author.id not in self.authorized:
            self.bot.loop.create_task(
                self.handle_err_message(ctx, "You cannot perform this action")
            )
            return False
        if ctx.guild.id in self.running_game:
            if self.running_game[ctx.guild.id].running:
                self.bot.loop.create_task(
                    self.handle_err_message(ctx, "Another game is running!")
                )
                return False
        return True

    @Cog.listener()
    async def on_message(self, msg: Message):
        if msg.author.bot:
            return

    # @mg_game.command(description="Initiate Squidgame")
    # async def start(self, ctx: ApplicationContext):
    #     await ctx.respond(
    #         "You will be initiating squid game for this guild\nPlease configure a settings below"
    #     )

    @mg_game.command()
    @option(name="role", type=Role, description="Player's role who join the game")
    @option(
        name="segements",
        type=int,
        description="Specify how many segements until the game is over",
        min_value=1,
    )
    @option(
        name="limit",
        type=int,
        description="Specify the time limit until the game is over (in minutes)",
        min_value=1,
    )
    async def glass_game(
        self, ctx: ApplicationContext, role: Role, limit: int, segements: int
    ):
        players = [m async for m in ctx.guild.fetch_members() if m.get_role(role.id)]
        if not players:
            return await ctx.respond("No players were found on that role!")
        detail_embed = Embed(
            colour=Colour.blurple(),
            title="Game details",
            description=(
                f"**{len(players)} player(s) found!**\n"
                + f"**TIME LIMIT IS: {limit} MINUTES!**\n"
                + "Rules:\n"
                + f"There will be {segements} bridge segments\n"
                + "Select the button bellow to reveal whether the bridge is safe or not\n"
                + "If you fail the bridge, you will be eliminated directly\n"
                + "If the time limit runs out, before segments reached "
                + "everyone in this stage gonna fail"
            ),
        )
        await ctx.respond(f"{role.mention} Prepare your game!", embed=detail_embed)
        shuffle(players)
        await ctx.channel.send(
            f"Please watch the play order {role.mention}\n"
            + ", ".join(f"({idx}. {m.mention})" for idx, m in enumerate(players, 1))
        )
        await asyncio.sleep(5)
        settings = BridgeGameSettings(players.pop(0), 1, players, players)
        view = BridgeGameView(self.bot, settings, limit * 60)
        view.msg = await ctx.followup.send(
            f"GAME START!\n{GLASS_GAME_FORMATTER.format(settings.segment, settings.turn.mention)}",
            view=view,
            wait=True,
            file=settings.generate_image(),
        )

    @slash_command()
    @option(name="user", type=Member)
    async def switch_turn(self, ctx: ApplicationContext, user: Member):
        await ctx.respond(f"{ctx.author.mention} Switched turn to {user.mention}")
