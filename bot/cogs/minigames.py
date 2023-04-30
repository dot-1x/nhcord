from __future__ import annotations
import asyncio
import json
from copy import copy
from random import shuffle
from typing import TYPE_CHECKING, Dict, List

import discord
from discord import Colour, option
from discord.ext.commands import Context

from ..models.minigames import (
    RunningGame,
    BridgeGameView,
)
from ..data.minigames import BridgeGameSettings

if TYPE_CHECKING:
    from ..bot import NhCord

__all__ = ("MinigamesCog",)


class MinigamesCog(discord.Cog):
    mg_game = discord.SlashCommandGroup("mg", "Main commands for minigames related")

    def __init__(self, bot: NhCord) -> None:
        self.bot = bot
        with open(
            "bot/data/minigames/minigames_settings.json", "r", encoding="utf-8"
        ) as settings:
            setting = json.load(settings)
            self.authorized: List[int] = setting["auth_command"]
        self.running_game: Dict[int, RunningGame] = {}

    async def handle_err_message(
        self, ctx: discord.ApplicationContext | Context, message: str
    ):
        if isinstance(ctx, discord.ApplicationContext):
            await ctx.response.send_message(message, ephemeral=True)
        else:
            await ctx.reply(message)

    async def cog_command_error(
        self, ctx: discord.ApplicationContext, error: Exception
    ) -> None:
        if isinstance(error, discord.CheckFailure):
            self.bot.log.warning(f"Check failed invoked by {ctx.author}")
        else:
            raise error

    def cog_check(self, ctx: discord.ApplicationContext | Context):
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

    @discord.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return
        print("hello world")

    @mg_game.command(description="Squid game - glass game")
    @option(name="role", type=discord.Role, description="Allowed Role to play the game")
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
    @option(
        name="loser_role",
        type=discord.Role,
        description="Assigned role who lose the game",
        required=False,
        default=None,
    )
    async def glass_game(
        self,
        ctx: discord.ApplicationContext,
        role: discord.Role,
        limit: int,
        segements: int,
        loser_role: discord.Role | None = None,
    ):
        players = [m async for m in ctx.guild.fetch_members() if m.get_role(role.id)]
        if not players:
            return await ctx.respond("No players were found on that role!")
        detail_embed = discord.Embed(
            colour=Colour.blurple(),
            title="Game details",
            description=(
                f"**{len(players)} player(s) found!**\n"
                + f"**TIME LIMIT IS: {limit} MINUTES!**\n"
                + "Rules:\n"
                + f"There will be **{segements}** bridge segments\n"
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
        settings = BridgeGameSettings(
            players.pop(0), segements, players, copy(players), loser_role=loser_role
        )
        view = BridgeGameView(self.bot, settings, limit * 60)
        file, embed = settings.generate_image()
        view.msg = await ctx.followup.send(
            f"GAME START!\n{settings.turn.mention}'s turn",
            view=view,
            wait=True,
            file=file,
            embed=embed,
        )
        view.timeleft = await ctx.channel.send(f"Timeleft: {60*limit}s")
        self.bot.loop.create_task(view.countdown())

    @mg_game.command(description="red green game based on questions")
    @option(
        name="quests",
        type=discord.Attachment,
        description="A file that contains questions format",
    )
    @option(name="role", type=discord.Role, description="Allowed Role to play the game")
    @option(
        name="loser_role",
        type=discord.Role,
        description="Assigned role who lose the game",
        required=False,
        default=None,
    )
    async def red_green(
        self,
        ctx: discord.ApplicationContext,
        quests: discord.Attachment,
        role: discord.Role,
        loser_role: discord.Role,
    ):
        players = [m async for m in ctx.guild.fetch_members() if m.get_role(role.id)]
        if not players:
            return await ctx.respond("No players were found on that role!")
        quest = json.loads(await quests.read())
        await ctx.respond(f"{len(quest)} quest(s) found!")
        print(loser_role)
