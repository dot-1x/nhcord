from __future__ import annotations
import asyncio
import csv
import json
from io import StringIO
from datetime import datetime, timedelta
from copy import copy
from random import choice, shuffle
from typing import TYPE_CHECKING, Dict, List

import discord
from discord import Colour, option
from discord.ext import commands

from bot.utils.check import is_admin

from ..models.minigames import (
    RunningGame,
    BridgeGameView,
    RGGameBase,
    RGPlayerData,
    RGQuestion,
)
from ..data.minigames import BridgeGameSettings, RedGreenGameSettings
from ..utils.minigames import get_member_by_role

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
        self, ctx: discord.ApplicationContext | commands.Context, message: str
    ):
        if isinstance(ctx, discord.ApplicationContext):
            await ctx.response.send_message(message)
        else:
            await ctx.reply(message)

    async def cog_command_error(
        self, ctx: discord.ApplicationContext, error: Exception
    ) -> None:
        if isinstance(error, discord.CheckFailure):
            self.bot.log.warning(f"Check failed invoked by {ctx.author}")
        else:
            raise error

    def cog_check(self, ctx: discord.ApplicationContext | commands.Context):
        if not is_admin(ctx.author):
            self.bot.loop.create_task(
                self.handle_err_message(ctx, "You cannot perform this action")
            )
            return False
        if isinstance(ctx, discord.ApplicationContext):
            opts = ctx.selected_options
            if (
                opts
                and any(opt for opt in opts if opt.get("name") == "loser_role")
                and not ctx.guild.me.guild_permissions.manage_roles
            ):
                self.bot.loop.create_task(
                    self.handle_err_message(
                        ctx, "Bot needs a permission to change role!"
                    )
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
            if msg.content.startswith("."):
                return
            if msg.author.id not in settings.registered_player:
                return print(f"player {msg.author} not registered!")
            player = settings.registered_player[msg.author.id]
            if not settings.allowed:
                return settings.eliminate_player(player.author)
            if not settings.answer:
                return
            if player.is_afk():
                print(f"Player {msg.author} is afk")
                return settings.eliminate_player(player.author)
            player.afk_counter = None  # remove the afk from player
            if player.correct >= settings.min_correct:
                return
            if not player.valid_turn():
                return
            if msg.content.lower() == settings.answer.lower():
                player.answered = True
                player.correct += 1
                print(f"{msg.author} answered correct")
            else:
                player.last_wrong = datetime.now()
                print(f"{msg.author} answered wrong")

    @mg_game.command(description="Squid game - glass game")
    @option(
        name="role",
        type=discord.Role,
        description="Allowed Role to play the game",
    )
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
    @option(
        name="winner_role",
        type=discord.Role,
        description="Assigned role who win the game",
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
        winner_role: discord.Role | None = None,
    ):
        await ctx.defer()
        if not isinstance(ctx.channel, discord.TextChannel):
            return await ctx.respond("Must be in text channel")
        if role == loser_role or (
            winner_role and loser_role and winner_role == loser_role
        ):
            return await ctx.respond(
                "Cannot assign same role for player and loser", ephemeral=True
            )
        players = [
            member async for member in get_member_by_role(ctx.guild, role, loser_role)
        ]
        if not players:
            return await ctx.respond("No players were found on that role!")
        detail_embed = discord.Embed(
            colour=Colour.blurple(),
            title="Game details",
            description=(
                "Rules:\n"
                + f"There will be **{segements}** bridge **segments**\n"
                + "Select the button bellow to reveal whether the bridge is safe or not\n"
                + "If you fail the bridge, you will be eliminated directly\n"
                + "If the time limit runs out, before **segments** reached "
                + "everyone in this stage gonna fail"
            ),
            fields=[
                discord.EmbedField("Players", str(len(players))),
                discord.EmbedField("Time Limit", f"{limit} minute(s)"),
                discord.EmbedField("Loser role", str(loser_role)),
                discord.EmbedField("Winner role", str(winner_role)),
            ],
        )
        await ctx.respond(f"{role.mention} Prepare your game!", embed=detail_embed)
        shuffle(players)
        settings = BridgeGameSettings(
            channel_id=ctx.channel_id or 0,
            turn=players.pop(0),
            segments=segements,
            players=players,
            registered_player=copy(players),
            loser_role=loser_role,
            winner_role=winner_role,
            running=True,
        )
        settings.move_segments()
        view = BridgeGameView(
            self.bot,
            settings,
            ctx.author,
            ctx.channel,
            datetime.now() + timedelta(minutes=limit),
        )
        file, embed = settings.generate_image()
        await asyncio.sleep(5)
        view.msg = await ctx.followup.send(
            f"GAME START!\nTimeleft: <t:{round(view.deadline.timestamp())}:R>\n{settings.turn.mention}'s turn",
            view=view,
            wait=True,
            file=file,
            embed=embed,
        )

    @mg_game.command(description="red green game based on questions")
    @option(
        name="quests",
        type=discord.Attachment,
        description="A file that contains questions format",
    )
    @option(
        name="role",
        type=discord.Role,
        description="Allowed Role to play the game",
    )
    @option(
        name="limit",
        type=int,
        min_value=1,
        default=5,
        description="Set the times up limit (minutes) [5]",
    )
    @option(
        name="loser_role",
        type=discord.Role,
        description="Assigned role who lose the game [None]",
        required=False,
        default=None,
    )
    @option(
        name="timing_min",
        type=int,
        min_value=0,
        default=5,
        description="Set the min time between the red-green light (seconds) [5]",
    )
    @option(
        name="timing_max",
        type=int,
        min_value=10,
        default=10,
        description="Set the max time between the red-green light (seconds) [10]",
    )
    @option(
        name="min_correct",
        type=int,
        min_value=1,
        default=5,
        description="Set the minimum total correct answer to win the game [5]",
    )
    async def red_green(  # pylint: disable=too-many-locals
        self,
        ctx: discord.ApplicationContext,
        quests: discord.Attachment,
        role: discord.Role,
        limit: int,
        loser_role: discord.Role | None,
        timing_min: int,
        timing_max: int,
        min_correct: int,
    ):
        await ctx.defer()
        if role == loser_role:
            return await ctx.respond(
                "Cannot assign same role for player and loser", ephemeral=True
            )
        if timing_max == timing_min:
            return await ctx.respond(
                "The time between game cannot be same", ephemeral=True
            )
        if timing_min > timing_max:
            return await ctx.respond(
                "The minimum time cannot be higher than max time", ephemeral=True
            )

        players = {
            member.id: RGPlayerData(member)
            async for member in get_member_by_role(ctx.guild, role, None)
        }
        if not players:
            return await ctx.respond("No players were found on that role!")
        try:
            buffer = await quests.read()
            with StringIO(buffer.decode()) as csvf:
                reader = csv.DictReader(
                    csvf, delimiter=",", fieldnames=["questions", "answer"]
                )
                quest = [
                    RGQuestion(questions["questions"], questions["answer"])
                    for questions in reader
                ]
        except (KeyError, UnicodeDecodeError, IndexError):
            with open("data/example.csv", "r", encoding="UTF-8") as exp:
                return await ctx.respond(
                    f"Please use the following format:\n```csv\n{exp.read()}```"
                )
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
                discord.EmbedField(
                    "Timing between questions",
                    f"{timing_min}s - {timing_max}s",
                ),
                discord.EmbedField("Questions", f"{len(quest)} question(s)"),
                discord.EmbedField("Loser role", str(loser_role)),
                discord.EmbedField("Minimum correct answer", str(min_correct)),
            ],
            colour=discord.Colour.blurple(),
        )
        shuffle(quest)
        settings = RedGreenGameSettings(
            base=None,
            invoker=ctx.author,
            channel_id=ctx.channel_id or 0,
            registered_player=players,
            running=True,
            questions=quest,
            loser_role=loser_role,
            min_correct=min(len(quest), min_correct),
        )
        self.rg_game.update({ctx.channel_id or 0: settings})
        game = RGGameBase(settings, timing_max, timing_min, limit * 60, ctx.channel)
        settings.base = game
        await ctx.followup.send(embed=emb)

    @commands.command(name="rgsignal")
    async def set_rg_signal(self, ctx: commands.Context):
        if ctx.channel.id not in self.rg_game:
            return await ctx.reply("Currently no running game on this channel")
        settings = self.rg_game[ctx.channel.id]
        if not settings.base:
            raise ValueError("base rg game settings is not found!")
        if settings.base.is_done:
            return await ctx.reply("Game is done!")
        if choice([True, False]):
            if not settings.base.enabled:
                print("Starting questions")
                await settings.base.start_game()
            # await ctx.reply(":green_circle: :green_circle: :green_circle:")
            # question = await settings.generate_quest()
            # settings.allowed = True
            # await ctx.reply(question)
        else:
            await ctx.reply(":red_circle: :red_circle: :red_circle:")
            settings.base.enabled = False
            settings.allowed = False
