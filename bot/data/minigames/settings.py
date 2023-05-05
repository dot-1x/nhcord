from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List
from discord import Colour, Embed, Member, File, Role

from ...utils.minigames import create_image_grid


if TYPE_CHECKING:
    from ...models.minigames import RGQuestion, RGPlayerData

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
    questions: List[RGQuestion]
    registered_player: Dict[int, RGPlayerData]
    allowed: bool = False
    fail_player: List[Member] = field(default_factory=list)
    loser_role: Role | None = None
    answer: str | None = None

    async def generate_quest(self):
        quest = self.questions.pop()
        self.answer = quest.answer
        for _, player in self.registered_player.items():
            player.answered = False
            await asyncio.sleep(0)
        return quest.quest
    
    def eliminate_player(self, player: Member):
        elim = self.registered_player.pop(player.id)
        self.fail_player.append(elim.author)
        print(f"{elim.author} eliminated!")


@dataclass(slots=True)
class BridgeGameSettings(BaseSettings):
    turn: Member
    segments: int
    players: List[Member]
    registered_player: List[Member]
    safe_point: int = 0
    fail_player: List[Member] = field(default_factory=list)
    loser_role: Role | None = None
    segment: int = 1

    def new_turn(self):
        if not self.players:
            raise ValueError("no more players!")
        # self.players.append(self.turn)
        self.turn = self.players.pop(0)
        return self.turn

    def generate_image(self):
        blurry, safe_point = create_image_grid()
        self.safe_point = safe_point
        print(safe_point)
        blurry.save("blurry.png")
        img = File("blurry.png", "blurry.png")
        embed = Embed(
            title="Choose the bridge!",
            description=f"**Segments: {self.segment}**\n" + BRIDGE_RULES,
            colour=Colour.teal(),
        )
        embed.set_image(url="attachment://blurry.png")
        return img, embed
