from __future__ import annotations
import asyncio

from dataclasses import dataclass
from random import randint
from typing import TYPE_CHECKING

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
            self.limit -= 1
            await asyncio.sleep(1)
        self.enabled = False

    async def start_game(self):
        asyncio.get_running_loop().create_task(self.timer())
        while self.settings.questions and self.enabled:
            await self.channel.send(":green_circle: :green_circle: :green_circle:")
            question = self.settings.generate_quest()
            self.settings.allowed = True
            await self.channel.send(question)
            await asyncio.sleep(randint(self.timing_min, self.timing_max))
            await self.channel.send(":red_circle: :red_circle: :red_circle:")
            self.settings.allowed = False
            await asyncio.sleep(randint(self.timing_min, self.timing_max))

    async def done(self):
        passed_players = []
        while self.settings.registered_player:
            _, player = self.settings.registered_player.popitem()
            if player.correct > 4:
                passed_players.append(player)
            else:
                self.settings.fail_player.append(player.author)
        embed = discord.Embed(
            title="Final Stats!",
            fields=[
                discord.EmbedField(
                    "Passed player",
                    str(len(passed_players)),
                    inline=True,
                ),
                discord.EmbedField(
                    "Fail Player", str(len(self.settings.fail_player)), inline=True
                ),
            ],
            colour=discord.Colour.teal(),
        )
        await self.channel.send("Game OVER!", embed=embed)
