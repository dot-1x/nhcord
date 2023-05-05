from __future__ import annotations
import asyncio

from dataclasses import dataclass, field
from random import randint
from typing import TYPE_CHECKING
from datetime import datetime, timedelta

from discord import Member
import discord

if TYPE_CHECKING:
    from ...data.minigames import RedGreenGameSettings


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

    def valid_turn(self):
        if self.afk_counter and (datetime.now() - self.afk_counter) > timedelta(minutes=20):
            return False
        if self.answered:
            return False
        if self.last_wrong and (datetime.now() - self.last_wrong) < timedelta(minutes=5):
            print(f"{self.author} is on wrong cooldown!")
            return False
        return True


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
        while self.settings.registered_player:
            _, player = self.settings.registered_player.popitem()
            if player.correct > 4:
                passed_players.append(player)
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
                discord.EmbedField(
                    "Passed Players",
                    "\n".join(player.mention for player in passed_players),
                    inline=False,
                ),
                discord.EmbedField(
                    "Fail Players",
                    "\n".join(player.mention for player in fails),
                    inline=True,
                ),
            ],
            colour=discord.Colour.teal(),
        )
        await self.channel.send("Game OVER!", embed=embed)
