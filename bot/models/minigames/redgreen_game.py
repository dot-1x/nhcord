from __future__ import annotations
import asyncio

from dataclasses import dataclass, field
from random import randint
from typing import TYPE_CHECKING
from datetime import datetime, timedelta

import discord
from discord import Member

from ...utils.check import is_admin

if TYPE_CHECKING:
    from ...data.minigames import RedGreenGameSettings
    from bot.bot import NhCord


@dataclass
class RGQuestion:
    quest: str
    answer: str


@dataclass
class RGPlayerData:
    author: Member
    correct: int = 0
    answered: bool = False
    last_wrong: datetime | None = None
    afk_counter: datetime | None = field(default=datetime.now())

    def is_afk(self):
        if self.afk_counter and (datetime.now() - self.afk_counter) > timedelta(
            minutes=20
        ):
            return True
        return False

    def valid_turn(self):
        if self.answered:
            return False
        if self.last_wrong and (datetime.now() - self.last_wrong) < timedelta(
            minutes=5
        ):
            print(f"{self.author} is on wrong cooldown!")
            return False
        return True


class RGGameView(discord.ui.View):
    def __init__(self, bot: NhCord, game: RGGameBase):
        super().__init__(timeout=60 * 60, disable_on_timeout=True)
        self.bot = bot
        self.game = game

    @discord.ui.button(label="Start Game", style=discord.ButtonStyle.primary)
    async def start_game(self, _, interaction: discord.Interaction):
        if isinstance(interaction.user, discord.Member) and not is_admin(
            interaction.user
        ):
            return await interaction.response.send_message(
                "This button is not for you", ephemeral=True
            )
        await self.disable()
        await self.game.start_game()

    @discord.ui.button(label="Cancel Game", style=discord.ButtonStyle.danger)
    async def cancel_game(self, _, interaction: discord.Interaction):
        if isinstance(interaction.user, discord.Member) and not is_admin(
            interaction.user
        ):
            return await interaction.response.send_message(
                "This button is not for you", ephemeral=True
            )
        await self.disable()
        await self.game.start_game()

    async def disable(self):
        msg = self.message
        if msg:
            self.disable_all_items()
            await msg.edit(view=self)


class RGGameBase:
    def __init__(
        self,
        settings: RedGreenGameSettings,
        timing_max: int,
        timing_min: int,
        limit: int,
        channel: discord.TextChannel,
    ) -> None:
        self.limit = limit
        self.settings = settings
        self.timing_min = timing_min
        self.timing_max = timing_max
        self.enabled = True
        self.channel = channel

    async def timer(self):
        while self.limit > 0:
            if not self.enabled:
                return
            self.limit -= 1
            await asyncio.sleep(1)
        await self.done()

    async def start_game(self):
        asyncio.get_running_loop().create_task(self.timer())
        while self.settings.questions and self.enabled:
            await self.channel.send(":green_circle: :green_circle: :green_circle:")
            question = await self.settings.generate_quest()
            self.settings.allowed = True
            await self.channel.send(question)
            await asyncio.sleep(randint(self.timing_min, self.timing_max))
            await self.channel.send(":red_circle: :red_circle: :red_circle:")
            self.settings.allowed = False
            await asyncio.sleep(randint(self.timing_min, self.timing_max))
        await self.done()

    async def done(self):
        self.enabled = False
        passed_players: list[Member] = []
        fails = self.settings.fail_player
        loser_role = self.settings.loser_role
        while self.settings.registered_player:
            _, player = self.settings.registered_player.popitem()
            if player.correct > 4:
                passed_players.append(player.author)
            else:
                fails.append(player.author)
            await asyncio.sleep(0)
        embed = discord.Embed(
            title="Final Stats!",
            fields=[
                discord.EmbedField(
                    "Total Passed player",
                    str(len(passed_players)),
                    inline=True,
                ),
                discord.EmbedField("Total Fail Player", str(len(fails)), inline=True),
            ],
            colour=discord.Colour.teal(),
        )
        await self.channel.send("Game OVER!", embed=embed)
        if loser_role:
            for fail in fails:
                await fail.add_roles(
                    loser_role, reason="Losing the game"  # type: ignore
                )
