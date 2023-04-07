from dataclasses import dataclass, field
from typing import Tuple, List
from discord import Member, File

from ...utils.minigames import create_image_grid


@dataclass(slots=True)
class RedGreenGameSettings:
    allowed: bool = False
    fail_player: List[Member] = field(default_factory=list)
    questions: List[Tuple[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class BridgeGameSettings:
    turn: Member
    segment: int
    players: List[Member]
    registered_player: List[Member]
    safe_point: int = 0
    fail_player: List[Member] = field(default_factory=list)

    def new_turn(self):
        if not self.players:
            raise ValueError("no more players!")
        self.turn = self.players.pop(0)
        return self.turn

    def generate_image(self):
        blurry, safe_point = create_image_grid()
        self.safe_point = safe_point
        blurry.save("blurry.jpg")
        img = File("blurry.jpg", "blurry.jpg")
        return img
