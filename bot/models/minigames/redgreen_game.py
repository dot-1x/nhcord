from __future__ import annotations
import asyncio

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from datetime import datetime, timedelta

import discord
from discord import Member

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
    last_answer: str = ""
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

    async def validate_turn(self, msg: discord.Message):
        if self.answered:
            emb = discord.Embed(
                description=f"{msg.author.mention} already answered: {self.last_answer}"
            )
            await msg.delete()
            await msg.channel.send(embed=emb)
        if not self.answered:
            self.last_answer = msg.content
            self.answered = True


class RGGameBase:
    def __init__(
        self,
        settings: RedGreenGameSettings,
        limit: int,
        channel: discord.TextChannel,
    ) -> None:
        self.limit = limit
        self.settings = settings
        self.enabled = False
        self.channel = channel
        self.is_done = False

    # async def start_game(self):
    #     self.enabled = True
    #     self.settings.allowed = True
    #     while self.settings.questions and self.enabled and not self.is_done:
    #         question = await self.settings.generate_quest()
    #         await self.channel.send(question)
    #         await asyncio.sleep(randint(self.timing_min, self.timing_max))
    #     if not self.settings.questions:
    #         print("No more questions")
    #         await self.done()
    #     print("Stopped questions")
    async def start_timer(self):
        deadline = datetime.now() + timedelta(minutes=self.limit)
        while datetime.now() < deadline:
            await asyncio.sleep(1)
        await self.done()

    async def done(self):
        self.is_done = True
        passed_players: list[Member] = []
        fails = self.settings.fail_player
        # loser_role = self.settings.loser_role
        # while self.settings.registered_player:
        #     _, player = self.settings.registered_player.popitem()
        #     if player.correct >= self.settings.min_correct:
        #         passed_players.append(player.author)
        #     else:
        #         fails.append(player.author)
        #     await asyncio.sleep(0)
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
        await self.channel.send("Game over!")
