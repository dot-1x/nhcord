from __future__ import annotations

import asyncio
import json
from copy import copy
from datetime import datetime, timedelta
from random import choice, shuffle
from typing import TYPE_CHECKING, Dict, List

import discord
from discord import Colour, option
from discord.ext import commands

from ...data.minigames import BridgeGameSettings, RedGreenGameSettings
from ...models.minigames import (
    BridgeGameChoose,
    BridgeGameView,
    RGGameBase,
    RGPlayerData,
    RunningGame,
)
from ...utils.minigames import TIMELEFT, get_member_by_role
from .admin import AdminCog

if TYPE_CHECKING:
    from ...bot import NhCord


class MinigamesCog(AdminCog):
    mg_game = discord.SlashCommandGroup("mg", "Main commands for minigames related")

    def __init__(self, bot: NhCord) -> None:
        super().__init__(bot)
        self.bot = bot
        with open(
            "bot/data/minigames/minigames_settings.json", "r", encoding="utf-8"
        ) as settings:
            setting = json.load(settings)
            self.authorized: List[int] = setting["auth_command"]
        self.running_game: Dict[int, RunningGame] = {}
        self.rg_game: Dict[int, RedGreenGameSettings] = {}

    @discord.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return
        channel = msg.channel.id
        if self.rg_game and channel in self.rg_game:
            settings = self.rg_game[channel]
            if await self.bot.is_owner(msg.author):  # type: ignore
                return
            if msg.author.id not in settings.registered_player:
                await msg.delete()
                print(f"player {msg.author} not in list")
                return
            player = settings.registered_player[msg.author.id]
            if not settings.allowed:
                # await msg.delete()
                return settings.eliminate_player(player.author)

            if player.is_afk():
                return settings.eliminate_player(player.author, True)

            player.afk_counter = datetime.now()  # reset the afk from player
            await player.validate_turn(msg)

    @mg_game.command(description="Squid game - glass game")
    @option(
        name="role",
        type=discord.Role,
        description="Allowed Role to play the game",
    )
    @option(
        name="segments",
        type=int,
        description="Specify how many segments until the game is over",
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
        segments: int,
        loser_role: discord.Role | None = None,
        winner_role: discord.Role | None = None,
    ):
        # await ctx.defer()
        if not isinstance(ctx.channel, discord.TextChannel):
            return await ctx.respond("Must be in text channel")
        if role == loser_role or (
            winner_role and loser_role and winner_role == loser_role
        ):
            return await ctx.respond(
                "Cannot assign same role for player and loser", ephemeral=True
            )
        selected = BridgeGameChoose(ctx.guild, ctx.author)
        await ctx.respond(view=selected, ephemeral=True)
        timeout = await selected.wait()
        if timeout:
            return
        players = [player for player in selected.values if player.get_role(role.id)]
        if not players:
            return await ctx.respond("No players were found!", ephemeral=True)
        detail_embed = discord.Embed(
            colour=Colour.blurple(),
            title="Game details",
            description=(
                "Rules:\n"
                + f"There will be **{segments}** bridge **segments**\n"
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
        await ctx.send(f"{role.mention} Prepare your game!", embed=detail_embed)
        shuffle(players)
        settings = BridgeGameSettings(
            channel_id=ctx.channel_id or 0,
            turn=players.pop(0),
            segments=segments,
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
        view.msg = await ctx.send(
            "GAME START!\n"
            + TIMELEFT.format(time=round(view.deadline.timestamp()))
            + f"{settings.turn.mention}'s turn",
            view=view,
            file=file,
            embed=embed,
        )
        self.bot.loop.create_task(view.start_timer())

    @mg_game.command(description="red green game based on questions")
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
        name="min_correct",
        type=int,
        min_value=1,
        default=5,
        description="Set the minimum total correct answer to win the game [5]",
    )
    async def red_green(  # pylint: disable=too-many-locals
        self,
        ctx: discord.ApplicationContext,
        role: discord.Role,
        limit: int,
        loser_role: discord.Role | None,
        min_correct: int,
    ):
        await ctx.defer()
        if role == loser_role:
            return await ctx.respond(
                "Cannot assign same role for player and loser", ephemeral=True
            )

        players = {
            member.id: RGPlayerData(member)
            async for member in get_member_by_role(ctx.guild, role, None)
        }
        if not players:
            return await ctx.respond("No players were found on that role!")
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
                discord.EmbedField("Loser role", str(loser_role)),
                discord.EmbedField("Minimum correct answer", str(min_correct)),
            ],
            colour=discord.Colour.blurple(),
        )
        settings = RedGreenGameSettings(
            channel=ctx.channel,
            base=None,
            invoker=ctx.author,
            channel_id=ctx.channel_id or 0,
            registered_player=players,
            running=True,
            loser_role=loser_role,
            min_correct=min_correct,
        )
        self.rg_game.update({ctx.channel_id or 0: settings})
        game = RGGameBase(settings, limit, ctx.channel)
        settings.base = game
        deadline = datetime.now() + timedelta(minutes=limit)
        await ctx.send(content=f"{role.mention} prepare your game!")
        await ctx.followup.send(
            content=TIMELEFT.format(time=round(deadline.timestamp())),
            embed=emb,
        )
        self.bot.loop.create_task(game.start_timer())

    @commands.command(name="rgsignal")
    async def set_rg_signal(self, ctx: commands.Context):
        if ctx.channel.id not in self.rg_game:
            return await ctx.reply("Currently no running game on this channel")
        settings = self.rg_game[ctx.channel.id]
        if not settings.base:
            raise ValueError("base rg game settings is not found!")
        if settings.base.is_done:
            return await ctx.reply("Game is done!")
        settings.reset_turn()
        signal = choice([True, False])
        settings.allowed = signal
        await ctx.reply(":green_circle:" if signal else ":red_circle:")

    @commands.command(name="rgkill")
    async def terminate_rg(self, ctx: commands.Context):
        if ctx.channel.id not in self.rg_game:
            return await ctx.reply("Currently no running game on this channel")
        settings = self.rg_game[ctx.channel.id]
        if settings.base and not settings.base.is_done:
            await settings.base.done()
        del self.rg_game[ctx.channel.id]
        await ctx.reply("Succesfully removed current running game")
