from __future__ import annotations
import asyncio

from typing import TYPE_CHECKING, Optional, Sequence
from discord import (
    Bot,
    ButtonStyle,
    Colour,
    EmbedField,
    Interaction,
    Message,
    WebhookMessage,
    Embed,
)
from discord.ui import View, Button

if TYPE_CHECKING:
    from ...data.minigames import BridgeGameSettings

__all__ = ("BridgeGameView",)


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
        if self.view.settings.safe_point == int(self.custom_id or 1) - 1:
            self.view.settings.segment += 1
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
        switch_btn: Button["BridgeGameView"] = Button(
            style=ButtonStyle.success, label="Switch Turn", row=3
        )
        switch_btn.callback = self.check_switch  # type: ignore
        self.add_item(switch_btn)

    async def check_switch(self, interaction: Interaction):
        if interaction.user and interaction.user.id not in [732842920889286687]:
            return await interaction.response.send_message(
                "You cannot perform this action", ephemeral=True
            )
        try:
            await self.switch_turn()
            await interaction.response.send_message(
                f"Switched turn to {self.settings.turn}", ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message(
                "No more players to switch", ephemeral=True
            )

    async def edit_msg(self, content: str, generate: bool, **kwargs):
        if not self.msg:
            return None
        self.msg.attachments = []
        if generate:
            if self.settings.segment > self.settings.segments:
                return await self.done()
            file, embed = self.settings.generate_image()
            kwargs.update({"file": file})
            kwargs.update({"embed": embed})
        return await self.msg.edit(content=content, **kwargs)

    async def switch_turn(self):
        self.settings.fail_player.append(self.settings.turn)
        self.settings.new_turn()
        await self.edit_msg(f"{self.settings.turn.mention}'s turn", False)

    async def refresh_message(self):
        await self.edit_msg(f"{self.settings.turn.mention}'s turn", True)

    async def done(self):
        if self.msg and self.timeleft:
            self.disabled = True
            await self.timeleft.delete()
            fields = [
                EmbedField(name, str(val))
                for name, val in [
                    ("Player Alive", len(self.settings.players) + 1),
                    ("Player Failed", len(self.settings.fail_player)),
                ]
            ]
            self.disable_all_items()
            emb = Embed(title="Final Stats", fields=fields, colour=Colour.teal())
            emb.set_thumbnail(
                url="https://www.vsomglass.com/wp-content/uploads/2021/10/SQUID-GAME-GLASS-BRIDGE-1.jpg"
            )
            await self.msg.edit(
                "Congratulations!!! you have passed the game!",
                embed=emb,
                attachments=[],
                view=self,
            )
            self.settings.running = False

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
            await self.timeleft.delete()
            await self.msg.edit(
                content="TIMES UP!!\nNo one has manage to escape!", view=self
            )
            self.settings.running = False
