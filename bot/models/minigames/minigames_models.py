from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto

from typing import TYPE_CHECKING, Optional, Sequence
from discord import Bot, ButtonStyle, ComponentType, Interaction, WebhookMessage
from discord.ui import View, Button, Select

if TYPE_CHECKING:
    from ...data.minigames import BridgeGameSettings

GLASS_GAME_FORMATTER = "Segments: {}\n{}'s turn!\nWhich bridge is SAFE?!!!"


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
    ):
        super().__init__(
            style=ButtonStyle.primary,
            label=label,
            disabled=False,
            custom_id=custom_id,
            row=row,
        )

    async def callback(self, interaction: Interaction):
        if not self.view:
            raise ValueError("View not found!")
        if interaction.user != self.view.settings.turn:
            return await interaction.response.send_message(
                "This button is not for you!", ephemeral=True
            )
        if self.view.settings.safe_point == int(self.custom_id or 1):
            await interaction.response.send_message("You have success!", ephemeral=True)
        else:
            await interaction.response.send_message("You have failed!", ephemeral=True)
        self.view.settings.segment += 1
        await self.view.refresh_message()


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
        self.settings = settings
        self.bot = bot
        for num in range(4):
            btn = BridgeGameButton(
                label=str(num + 1),
                custom_id=str(num),
                row=1 if num < 2 else 2,
            )
            self.add_item(btn)
            self.childs.append(btn)

    async def edit_msg(self, content: str, **kwargs):
        if not self.msg:
            return None
        self.msg.attachments = []
        return await self.msg.edit(
            content=content, file=self.settings.generate_image(), **kwargs
        )

    async def switch_turn(self):
        await self.edit_msg(
            GLASS_GAME_FORMATTER.format(
                self.settings.segment, self.settings.new_turn().mention
            )
        )

    async def refresh_message(self):
        await self.edit_msg(
            GLASS_GAME_FORMATTER.format(
                self.settings.segment, self.settings.turn.mention
            )
        )


class MinigamesSelectRole(Select):
    def __init__(self) -> None:
        super().__init__(ComponentType.role_select, placeholder="Select A Roles")


class MiniGamesInitSettings(View):
    def __init__(self):
        super().__init__(timeout=5 * 60, disable_on_timeout=True)
