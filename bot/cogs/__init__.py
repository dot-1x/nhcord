from __future__ import annotations
from typing import TYPE_CHECKING

from .minigames import MinigamesCog
from .giveaway import GiveawayCog

if TYPE_CHECKING:
    from ..bot import NhCord

COGS = [GiveawayCog, MinigamesCog]


def setup(bot: NhCord):
    for cog in COGS:
        bot.log.info(f"Loaded Cog {str(cog)}")
        bot.add_cog(cog(bot))
