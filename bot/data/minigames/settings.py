from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from random import randint
from typing import TYPE_CHECKING, Dict, List, Literal
from discord import Colour, Embed, Member, File, Role, User

from ...utils.minigames import create_image_grid


if TYPE_CHECKING:
    from ...models.minigames import RGQuestion, RGPlayerData, RGGameBase

GLASS_GAME_FORMATTER = "Segments: {}\n{}'s turn!\nWhich bridge is SAFE?!!!"

BRIDGE_RULES = "Select the button bellow to reveal whether the bridge is safe or not\n\
If you fail the bridge, you will be eliminated directly\n\
If the time limit runs out, before segments reached\n\
everyone in this stage gonna fail"


@dataclass
class BaseSettings:
    channel_id: int
    running: bool


@dataclass(slots=True)
class RedGreenGameSettings(BaseSettings):
    base: RGGameBase | None
    invoker: Member
    questions: List[RGQuestion]
    registered_player: Dict[int, RGPlayerData]
    allowed: bool = False
    fail_player: List[Member] = field(default_factory=list)
    loser_role: Role | None = None
    answer: str | None = None
    min_correct: int = 5

    async def generate_quest(self):
        quest = self.questions.pop()
        self.answer = quest.answer
        for _, player in self.registered_player.items():
            player.answered = False
            await asyncio.sleep(0)
        return quest.quest

    def eliminate_player(self, player: Member | User):
        print(f"{player} eliminated")
        if self.loser_role:
            asyncio.get_running_loop().create_task(player.add_roles([self.loser_role]))  # type: ignore
        try:
            elim = self.registered_player.pop(player.id)
        except KeyError:
            self.fail_player.append(player)  # type: ignore
            return
        self.fail_player.append(elim.author)

    def switch_signal(self):
        ...


@dataclass(slots=True)
class BridgeGameSettings(BaseSettings):
    turn: Member
    segments: int
    players: List[Member]
    registered_player: List[Member]
    safe_point: int = 0
    fail_player: List[Member] = field(default_factory=list)
    loser_role: Role | None = None
    winner_role: Role | None = None
    segment: int = 1
    revealed_bridge: list[int] = field(default_factory=list)

    def move_segments(self):
        self.safe_point = randint(0, 3)
        print(self.safe_point)
        self.revealed_bridge = []

    async def new_turn(self, safe_pos: int | None):
        if safe_pos is not None:
            self.revealed_bridge.append(safe_pos)
        self.fail_player.append(self.turn)
        if self.loser_role:
            await self.turn.add_roles(self.loser_role)  # type: ignore
        if not self.players:
            raise ValueError("no more players!")
        # self.players.append(self.turn)
        self.turn = self.players.pop(0)
        return self.turn

    def generate_image(self, reveal: bool = False):
        if reveal:
            self.revealed_bridge = list(range(4))
        img = create_image_grid(self.revealed_bridge, self.safe_point)
        img.save("bridgechoose.png")
        img = File("bridgechoose.png", "bridgechoose.png")
        embed = Embed(
            title="Choose the bridge!",
            description=f"**Panel: {self.segment}**\n" + BRIDGE_RULES,
            colour=Colour.teal(),
        )
        embed.set_image(url="attachment://bridgechoose.png")
        return img, embed

    async def assign_role(self, target: Literal["winner", "loser", "failed"]):
        if self.loser_role and target == "loser":
            for fail in self.fail_player:
                await fail.add_roles(self.loser_role, reason="Losing the game")  # type: ignore
        elif self.winner_role and target == "winner":
            for winner in self.players:
                await winner.add_roles(
                    self.winner_role, reason="Winning the game"  # type: ignore
                )
        elif target == "failed" and self.loser_role:
            self.fail_player.append(self.turn)
            players = self.fail_player + self.players
            for player in players:
                await player.add_roles(self.loser_role)  # type: ignore
