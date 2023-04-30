from dataclasses import dataclass, field
from typing import Tuple, List
from discord import Colour, Embed, Member, File, Role

from ...utils.minigames import create_image_grid

GLASS_GAME_FORMATTER = "Segments: {}\n{}'s turn!\nWhich bridge is SAFE?!!!"

BRIDGE_RULES = "Select the button bellow to reveal whether the bridge is safe or not\n\
If you fail the bridge, you will be eliminated directly\n\
If the time limit runs out, before segments reached\n\
everyone in this stage gonna fail"


@dataclass(slots=True)
class RedGreenGameSettings:
    allowed: bool = False
    fail_player: List[Member] = field(default_factory=list)
    questions: List[Tuple[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class BridgeGameSettings:
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
