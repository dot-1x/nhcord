from __future__ import annotations

from typing import TYPE_CHECKING

from .modmail import ModMail

if TYPE_CHECKING:
    from ..bot import NhCord

EVENTS = [ModMail]


def setup(bot: NhCord):
    for cog in EVENTS:
        bot.log.info(f"Loaded Cog {str(cog)}")
        bot.add_cog(cog(bot))
