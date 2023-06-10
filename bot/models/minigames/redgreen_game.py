from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import discord
from discord import Member

from bot.logs.custom_logger import BotLogger

if TYPE_CHECKING:
    from ...data.minigames import RedGreenGameSettings


_log = BotLogger("[RG MINIGAMES]")


@dataclass
class RGQuestion:
    quest: str
    answer: str
    choices: str = ""


@dataclass
class RGPlayerData:
    author: Member
    correct: int = 0
    answered: bool = False
    last_wrong: datetime | None = None
    last_answer: str = ""
    afk_counter: datetime = field(default=datetime.now())

    def is_afk(self):
        if (datetime.now() - self.afk_counter) > timedelta(minutes=20):
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

    async def validate_turn(self, msg: discord.Message, question: RGQuestion | None):
        if not question:
            return
        # if self.answered:
        #     emb = discord.Embed(
        #         description=f"{msg.author.mention} already answered: {self.last_answer}",
        #         color=discord.Color.blue(),
        #     )
        #     await msg.channel.send(embed=emb)
        # await msg.delete()
        # if not self.answered:
        self.last_answer = msg.content
        if self.last_answer.lower() == question.answer.lower():
            _log.info("%s answered correct", self.author.name)
            self.correct += 1
        else:
            _log.warning("%s answered wrong", self.author.name)
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

    async def start_timer(self):
        deadline = datetime.now() + timedelta(minutes=self.limit)
        while datetime.now() < deadline:
            await asyncio.sleep(1)
        await self.done()

    async def done(self):
        if self.is_done:
            return
        self.is_done = True
        # self.settings.allowed = False
        remain = list(self.settings.registered_player.values())
        for player in remain:
            if player.correct < self.settings.min_correct:
                await self.settings.eliminate_player(player.author, 2)
        emb = discord.Embed(description="**GAME OVER !!**", color=discord.Color.red())
        await self.channel.send(embed=emb)
