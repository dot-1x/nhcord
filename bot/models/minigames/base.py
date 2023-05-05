from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from ...data.minigames.settings import BridgeGameSettings, RedGreenGameSettings

__all__ = ("RunningGame", "GameType")


class GameType(Enum):
    GLASS_BRIDGE = auto()
    RED_GREEN = auto()

    def __str__(self) -> str:
        return self.name.replace("_", " ").title()


@dataclass
class RunningGame:
    games: Optional[GameType]
    settings: BridgeGameSettings | RedGreenGameSettings
