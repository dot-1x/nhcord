from __future__ import annotations
import asyncio
from dataclasses import dataclass
from enum import Enum, auto

from typing import TYPE_CHECKING, Optional, Sequence
from discord import (
    Bot,
    ButtonStyle,
    Interaction,
    Message,
    WebhookMessage,
)
from discord.ui import View, Button

if TYPE_CHECKING:
    from ...data.minigames import BridgeGameSettings


class GameType(Enum):
    GLASS_BRIDGE = auto()
    RED_GREEN = auto()


@dataclass
class RunningGame:
    running: bool
    games: Optional[GameType]


class BridgeGameButton(Button["BridgeGameView"]):
    def __init__(
        self,
        *,
        label: str | None = None,
        custom_id: str | None = None,
        row: int | None = None,
        **kwargs,
    ):
        super().__init__(
            style=ButtonStyle.primary
            if not kwargs.get("disabled")
            else ButtonStyle.gray,
            label=label,
            custom_id=custom_id,
            row=row,
            **kwargs,
        )

    async def callback(self, interaction: Interaction):
        if not self.view:
            raise ValueError("View not found!")
        if interaction.user != self.view.settings.turn:
            return await interaction.response.send_message(
                "This button is not for you!", ephemeral=True
            )
        self.view.settings.segment += 1
        if self.view.settings.safe_point == int(self.custom_id or 1) - 1:
            await interaction.response.send_message("You have success!", ephemeral=True)
            await self.view.refresh_message()
        else:
            await interaction.response.send_message("You have failed!", ephemeral=True)
            await self.view.switch_turn()


class BridgeGameView(View):
    def __init__(
        self,
        bot: Bot,
        settings: BridgeGameSettings,
        timeout: float = 60,
    ):
        if timeout <= 0:
            raise ValueError("Time out must be higher than 0")
        super().__init__(timeout=timeout, disable_on_timeout=True)
        self.childs: Sequence[BridgeGameButton] = []
        self.msg: Optional[WebhookMessage] = None
        self.timeleft: Message | None = None
        self.settings = settings
        self.bot = bot
        self.disabled = False
        idx = 1
        for row in range(1, 3):
            for col in range(1, 4):
                btn = BridgeGameButton(
                    label=str(idx) if col % 2 else "-",
                    custom_id=str(idx) if col % 2 else None,
                    row=row,
                    disabled=not (col % 2),
                )
                if col % 2:
                    idx += 1
                self.add_item(btn)
                self.childs.append(btn)

    async def edit_msg(self, content: str, generate: bool, **kwargs):
        if not self.msg:
            return None
        self.msg.attachments = []
        if generate:
            file, embed = self.settings.generate_image()
            kwargs.update({"file": file})
            kwargs.update({"embed": embed})
        return await self.msg.edit(content=content, **kwargs)

    async def switch_turn(self):
        self.settings.new_turn()
        await self.edit_msg(f"{self.settings.turn.mention}'s turn", False)

    async def refresh_message(self):
        await self.edit_msg(f"{self.settings.turn.mention}'s turn", True)

    async def countdown(self):
        while not self.timeleft:
            await asyncio.sleep(0)
        for time in range(int(self.timeout or 1), 0, -1):
            if self.disabled:
                return
            await self.timeleft.edit(content=f"Timeleft: {time}s")
            await asyncio.sleep(1)
        await self.on_timeout()
        self.stop()

    async def on_timeout(self) -> None:
        if self.msg and not self.disabled and self.timeleft:
            self.disabled = True
            self.disable_all_items()
            self.msg.embeds = []
            self.msg.attachments = []
            await self.msg.edit(content="No one has manage to escape!", view=self)
