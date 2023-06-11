from __future__ import annotations

from typing import TYPE_CHECKING
from discord import Cog
import discord
from discord.interactions import Interaction


if TYPE_CHECKING:
    from bot.bot import NhCord

CREATE_TICKET_MSG = "Hello {author}, to contact our discord staff, please fill form by clicking button below"


class TicketModal(discord.ui.Modal):
    def __init__(
        self,
        bot: NhCord,
        message: discord.Message | None,
        custom_id: str | None = None,
    ) -> None:
        super().__init__(title="Submit a ticket", custom_id=custom_id, timeout=180)
        self.ticket_title = discord.ui.InputText(label="Ticket title")
        self.content = discord.ui.InputText(
            label="Ticket content", style=discord.InputTextStyle.long
        )
        self.add_item(self.ticket_title)
        self.add_item(self.content)
        self.msg = message
        self.bot = bot

    async def callback(self, interaction: Interaction):
        await interaction.response.send_message(
            "Thank you for your ticket, our staff will be in respond as soon as possible"
        )
        if self.msg:
            await self.msg.edit(content="Ticket has been submitted", view=None)

    async def create_ticket(self):
        ...


class TicketView(discord.ui.View):
    def __init__(self, bot: NhCord):
        super().__init__(timeout=180, disable_on_timeout=True)
        self.bot = bot

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.success)
    async def create_ticket(self, _, interaction: discord.Interaction):
        await interaction.response.send_modal(
            TicketModal(self.bot, message=interaction.message)
        )


class ModMail(Cog):
    def __init__(self, bot: NhCord) -> None:
        self.bot = bot

    @property
    def tickets(self):
        return self.bot.tickets

    @Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot or msg.guild:
            return
        registered = self.is_registered(msg.author.id)
        if registered:
            return await msg.reply(
                f"A ticket already registered on: {registered.ticket_channel.mention}"
            )
        await msg.reply(
            CREATE_TICKET_MSG.format(author=msg.author.mention),
            view=TicketView(self.bot),
        )

    def is_registered(self, ids: int):
        return self.tickets.get(ids)
