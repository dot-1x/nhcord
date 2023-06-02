from __future__ import annotations
from datetime import datetime

from typing import TYPE_CHECKING, Optional, Sequence
from discord import (
    Bot,
    ButtonStyle,
    Colour,
    EmbedField,
    Interaction,
    Member,
    Message,
    TextChannel,
    User,
    WebhookMessage,
    Embed,
)
from discord.ui import View, Button

from ...utils.minigames.minigames_utils import TIMELEFT

if TYPE_CHECKING:
    from ...data.minigames import BridgeGameSettings

__all__ = ("BridgeGameView",)
THUMBNAIL_URL = (
    "https://www.vsomglass.com/wp-content/uploads/2021/10/SQUID-GAME-GLASS-BRIDGE-1.jpg"
)


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
            await interaction.response.send_message("You have success!", ephemeral=True)
            await self.view.new_segment()
        else:
            await interaction.response.send_message("You have failed!", ephemeral=True)
            await self.view.switch_turn(int(self.custom_id or 1) - 1)


class BridgeGameView(View):
    def __init__(
        self,
        bot: Bot,
        settings: BridgeGameSettings,
        invoker: User | Member,
        channel: TextChannel,
        timeout: datetime,
    ):
        super().__init__(
            timeout=(timeout - datetime.now()).total_seconds(), disable_on_timeout=True
        )
        self.deadline = timeout
        self.childs: Sequence[BridgeGameButton] = []
        self.msg: Optional[WebhookMessage | Message] = None
        self.settings = settings
        self.bot = bot
        self.disabled = False
        self.invoker = invoker
        self.channel = channel
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
                if col % 2:
                    self.childs.append(btn)
        switch_btn: Button["BridgeGameView"] = Button(
            style=ButtonStyle.success, label="Switch Turn", row=3
        )
        switch_btn.callback = self.check_switch  # type: ignore
        self.childs.append(switch_btn)  # type: ignore
        self.add_item(switch_btn)

    async def check_switch(self, interaction: Interaction):
        if interaction.user != self.invoker:
            return await interaction.response.send_message(
                "You cannot perform this action", ephemeral=True
            )
        await self.switch_turn(None)
        await interaction.response.send_message(
            f"Switched turn to {self.settings.turn}", ephemeral=True
        )

    async def new_segment(self):
        if not self.msg:
            print("message were not found!")
            return
        self.disable_all_items()
        file, embed = self.settings.generate_image(reveal=True)
        await self.msg.edit(file=file, embed=embed, view=self)
        self.settings.segment += 1
        if self.settings.segment > self.settings.segments:
            self.settings.segment = self.settings.segments
            return await self.done()
        # view = BridgeGameView(
        #     self.bot, self.settings, self.invoker, self.channel, self.deadline
        # )
        for child in self.childs:
            child.disabled = False
        self.settings.move_segments()
        file, embed = self.settings.generate_image()
        self.msg = await self.channel.send(
            content=TIMELEFT.format(time=round(self.deadline.timestamp()))
            + f"{self.settings.turn.mention}'s turn",
            file=file,
            embed=embed,
            view=self,
        )

    async def switch_turn(self, click_point: int | None):
        if not self.msg:
            print("message were not found!")
            return
        try:
            await self.settings.new_turn(click_point)
        except ValueError:
            return await self.done(kill=True)
        file, embed = self.settings.generate_image(reveal=False)
        await self.msg.edit(file=file, embed=embed, view=self)

    async def done(self, kill=False):
        if self.msg:
            self.stop()
            fails = self.settings.fail_player
            players = self.settings.players
            if self.settings.turn not in fails:
                players.append(self.settings.turn)
            self.disabled = True
            fields = [
                EmbedField(name, str(val), inline)
                for name, val, inline in [
                    ("Player Alive", len(players), True),
                    ("Player Failed", len(fails), True),
                    ("Last segment", self.settings.segment, True),
                ]
            ]
            self.disable_all_items()
            emb = Embed(title="Final Stats", fields=fields, colour=Colour.teal())
            emb.set_thumbnail(url=THUMBNAIL_URL)
            await self.msg.edit(view=self)
            await self.msg.reply(
                content=TIMELEFT.format(time=round(self.deadline.timestamp()))
                + (
                    "Congratulations!! you have won the game"
                    if not kill
                    else "Game Over!! everyone is failed"
                ),
                embed=emb,
            )
            self.settings.running = False
            if kill:
                await self.settings.assign_role("failed")
                return
            await self.settings.assign_role("winner")
            await self.settings.assign_role("loser")

    async def on_timeout(self):
        await self.done(True)
