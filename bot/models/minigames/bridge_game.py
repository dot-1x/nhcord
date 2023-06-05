from __future__ import annotations
from asyncio import get_running_loop
import asyncio
from datetime import datetime

from typing import TYPE_CHECKING, Optional, Sequence
from discord import (
    Colour,
    Interaction,
    Message,
    TextChannel,
    WebhookMessage,
    Embed,
)
import discord
from discord.ui import View, Button

from bot.logs.custom_logger import BotLogger

from ...utils.minigames.minigames_utils import TIMELEFT

if TYPE_CHECKING:
    from bot.bot import NhCord
    from ...data.minigames import BridgeGameSettings

__all__ = ("BridgeGameView", "BridgeGameChoose")
THUMBNAIL_URL = (
    "https://www.vsomglass.com/wp-content/uploads/2021/10/SQUID-GAME-GLASS-BRIDGE-1.jpg"
)

_log = BotLogger("[MG BRIDGE]")


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
            style=discord.ButtonStyle.primary
            if not kwargs.get("disabled")
            else discord.ButtonStyle.gray,
            label=label,
            custom_id=custom_id,
            row=row,
            **kwargs,
        )

    async def callback(self, interaction: Interaction):
        if not self.view:
            raise ValueError("View not found!")
        if (
            isinstance(interaction.user, discord.Member)
            and interaction.user != self.view.settings.turn
            # and not is_admin(interaction.user)
        ):
            return await interaction.response.send_message(
                "This button is not for you!", ephemeral=True
            )
        if self.view.settings.safe_point == int(self.label or 1) - 1:
            await interaction.response.send_message("You have success!", ephemeral=True)
            await self.view.new_segment()
        else:
            await interaction.response.send_message("You have failed!", ephemeral=True)
            await self.view.switch_turn(int(self.label or 1) - 1)


class BridgeGameChoose(View):
    def __init__(
        self,
        guild: discord.Guild,
        author: discord.Member | discord.User,
        select_opt: discord.ui.Select | None = None,
    ):
        super().__init__(timeout=600, disable_on_timeout=True)
        self.author = author
        self.select = select_opt
        self.guild = guild
        self.values: list[discord.Member] = []

    @discord.ui.select(
        discord.ComponentType.user_select,
        placeholder="Select user to play",
        min_values=2,
        max_values=25,
    )
    async def select_user(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        await interaction.response.defer(ephemeral=True)
        if interaction.user != self.author:
            return await interaction.response.send_message(
                "This button is not for you", ephemeral=True
            )
        self.values = [val for val in select.values if isinstance(val, discord.Member)]
        await interaction.followup.send(
            f"Selected {len(self.values)} members", ephemeral=True
        )

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.primary)
    async def confirm(self, _, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Game started! {len(self.values)} players are in", ephemeral=True
        )
        self.stop()


class BridgeGameView(View):
    def __init__(
        self,
        bot: NhCord,
        settings: BridgeGameSettings,
        invoker: discord.User | discord.Member,
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
                    # custom_id=str(idx) if col % 2 else None,
                    custom_id=None,
                    row=row,
                    disabled=not (col % 2),
                )
                if col % 2:
                    idx += 1
                    self.childs.append(btn)
                self.add_item(btn)
        switch_btn: Button["BridgeGameView"] = Button(
            style=discord.ButtonStyle.success, label="Switch Turn", row=3
        )
        switch_btn.callback = self.check_switch  # type: ignore
        self.childs.append(switch_btn)  # type: ignore
        self.add_item(switch_btn)

    async def check_switch(self, interaction: Interaction):
        if interaction.user != self.settings.turn:
            return await interaction.response.send_message(
                "You cannot perform this action", ephemeral=True
            )
        await self.switch_turn(None)
        await interaction.response.send_message(
            f"Switched turn to {self.settings.turn}", ephemeral=True
        )

    async def new_segment(self):
        if not self.msg:
            _log.warning("message were not found!")
            return
        # self.disable_all_items()
        file, embed = self.settings.generate_image(reveal=True)
        await self.msg.edit(file=file, embed=embed, view=None)
        self.settings.segment += 1
        if self.settings.segment > self.settings.segments:
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
            _log.warning("message were not found!")
            return
        try:
            await self.settings.new_turn(click_point)
        except ValueError:
            return await self.done()
        kwargs = {}
        if click_point is not None:
            file, embed = self.settings.generate_image(reveal=False)
            kwargs.update({"file": file})
            kwargs.update({"embed": embed})
        await self.msg.edit(
            content=TIMELEFT.format(time=round(self.deadline.timestamp()))
            + f"{self.settings.turn.mention}'s turn",
            view=self,
            **kwargs,
        )

    async def done(self):
        if self.msg and not self.disabled:
            self.stop()
            _log.info("Game done!")
            self.disabled = True
            kill = self.settings.segment < self.settings.segments
            fails = self.settings.fail_player
            players = self.settings.players
            if self.settings.turn not in fails and kill:
                _log.info("turned player appended to fails")
                fails.append(self.settings.turn)
            if not kill:
                _log.info("turned player appended to players")
                players.append(self.settings.turn)
            if kill:
                fails.extend(players)
                players = []
            fields = [
                discord.EmbedField(name, str(val), inline)
                for name, val, inline in [
                    ("Player Alive", len(players), True),
                    ("Player Failed", len(fails), True),
                    ("Last segment", self.settings.segment - 1, True),
                ]
            ]
            self.disable_all_items()
            emb = Embed(title="Final Stats", fields=fields, colour=Colour.teal())
            emb.set_thumbnail(url=THUMBNAIL_URL)
            await self.msg.edit(view=self)
            player = (
                self.settings.winner_role.mention
                if self.settings.winner_role
                else "Player"
            )
            await self.msg.reply(
                content=TIMELEFT.format(time=round(self.deadline.timestamp()))
                + (
                    "**Congratulations!!** you have won the game"
                    if not kill
                    else f"**Game Over!!** All {player} is failed"
                ),
                embed=emb,
            )
            self.settings.running = False
            if kill:
                await self.settings.assign_role("failed")
            else:
                get_running_loop().create_task(self.settings.assign_role("winner"))
                get_running_loop().create_task(self.settings.assign_role("loser"))

    async def start_timer(self):
        while datetime.now() < self.deadline and not self.disabled:
            await asyncio.sleep(1)
        _log.info("Timer disabled")
        await self.done()
