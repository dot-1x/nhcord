from __future__ import annotations
import asyncio
import json
from datetime import datetime
from copy import copy
from random import shuffle
from typing import TYPE_CHECKING, Dict, List

import discord
from discord import Colour, option
from discord.ext.commands import Context

from ..models.minigames import (
    RunningGame,
    BridgeGameView,
    RGGameBase,
    RGPlayerData,
    RGQuestion,
)
from ..data.minigames import BridgeGameSettings, RedGreenGameSettings

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
        self.rg_game: Dict[int, RedGreenGameSettings] = {}

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
        channel_id = (
            ctx.interaction.channel_id
            if isinstance(ctx, discord.ApplicationContext)
            else ctx.channel.id
        )
        cmd_name = ctx.command.name if ctx.command else "no name"
        if (
            channel_id in self.running_game
            and self.running_game[channel_id].settings.running
            and cmd_name != "stop_game"
        ):
            self.bot.loop.create_task(
                self.handle_err_message(ctx, "Another game is running!")
            )
            return False
        return True

    @discord.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return
        channel = msg.channel.id
        if self.rg_game and channel in self.rg_game:
            settings = self.rg_game[channel]
            if not settings.answer or not msg.author.id in settings.registered_player:
                return
            player = settings.registered_player[msg.author.id]
            if player.correct > 4:
                return
            if not settings.allowed:
                return settings.eliminate_player(msg.author)
            if not player.valid_turn():
                return
            player.afk_counter = None # remove the afk from player
            if msg.content.lower() == settings.answer.lower():
                player.answered = True
                player.correct += 1
                print(f"{msg.author} answered correct")
            else:
                player.last_wrong = datetime.now()
                print(f"{msg.author} answered wrong")


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
                "Rules:\n"
                + f"There will be **{segements}** bridge segments\n"
                + "Select the button bellow to reveal whether the bridge is safe or not\n"
                + "If you fail the bridge, you will be eliminated directly\n"
                + "If the time limit runs out, before segments reached "
                + "everyone in this stage gonna fail"
            ),
            fields=[
                discord.EmbedField("Players", str(len(players))),
                discord.EmbedField("Time Limit", f"{limit} minute(s)"),
                discord.EmbedField("Loser role", str(loser_role)),
            ],
        )
        await ctx.respond(f"{role.mention} Prepare your game!", embed=detail_embed)
        shuffle(players)
        await ctx.channel.send(
            f"Please watch the play order {role.mention}\n"
            + ", ".join(f"({idx}. {m.mention})" for idx, m in enumerate(players, 1))
        )
        settings = BridgeGameSettings(
            channel_id=ctx.channel_id or 0,
            turn=players.pop(0),
            segments=segements,
            players=players,
            registered_player=copy(players),
            loser_role=loser_role,
            running=True,
        )
        view = BridgeGameView(self.bot, settings, limit * 60)
        file, embed = settings.generate_image()
        await asyncio.sleep(5)
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
        name="limit",
        type=int,
        min_value=1,
        default=5,
        description="Set the times up limit (minutes)",
    )
    @option(
        name="loser_role",
        type=discord.Role,
        description="Assigned role who lose the game",
        required=False,
        default=None,
    )
    @option(
        name="timing_min",
        type=int,
        min_value=0,
        default=5,
        description="Set the min time between the red-green light (seconds)",
    )
    @option(
        name="timing_max",
        type=int,
        min_value=10,
        default=10,
        description="Set the max time between the red-green light (seconds)",
    )
    async def red_green(
        self,
        ctx: discord.ApplicationContext,
        quests: discord.Attachment,
        role: discord.Role,
        limit: int,
        loser_role: discord.Role | None,
        timing_min: int,
        timing_max: int,
    ):
        await ctx.defer()
        if timing_max == timing_min:
            return await ctx.respond("The time between game cannot be same")
        if timing_min > timing_max:
            return await ctx.respond("The minimum time cannot be higher than max time")

        players = {
            m.id: RGPlayerData(m)
            async for m in ctx.guild.fetch_members()
            if m.get_role(role.id) and m.bot is False
        }
        if not players:
            return await ctx.respond("No players were found on that role!")
        quest = [RGQuestion(q["q"], q["a"]) for q in json.loads(await quests.read())]
        emb = discord.Embed(
            title="Game Details",
            description="There will be some questions appear on the chat"
            + "\nYou will be eliminated if:"
            + "\nYou were typing when the light is **RED**"
            + "\nYou were typing wrong answer"
            + "\nYou were AFK for limited time",
            fields=[
                discord.EmbedField("Players", str(len(players))),
                discord.EmbedField("Time Limit", f"{limit}m"),
                discord.EmbedField("Timing", f"{timing_min}s - {timing_max}s"),
                discord.EmbedField("Quests", f"{len(quest)} quest(s)"),
                discord.EmbedField("Loser role", str(loser_role)),
            ],
            colour=discord.Colour.blurple(),
        )
        shuffle(quest)
        settings = RedGreenGameSettings(
            channel_id=ctx.channel_id or 0,
            registered_player=players,
            running=True,
            questions=quest,
            loser_role=loser_role,
        )
        self.rg_game.update({ctx.channel_id or 0: settings})
        game = RGGameBase(settings, timing_max, timing_min, limit * 60, ctx.channel)
        await ctx.followup.send(embed=emb)
        await ctx.send("Game start soon!")
        await asyncio.sleep(5)
        await game.start_game()
