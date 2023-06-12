from __future__ import annotations

import asyncio
import secrets
from typing import TYPE_CHECKING

import discord
from discord import Cog, PermissionOverwrite
from discord.ext import commands
from discord.interactions import Interaction

from ..config import CONFIG
from ..models.modmail.ticket import Ticket
from ..utils.check import is_admin

if TYPE_CHECKING:
    from ..bot import NhCord

CREATE_TICKET_MSG = "Hello {author}, to contact our discord staff,\
please fill form by clicking button below"
ALLOW_READ = PermissionOverwrite(
    send_messages=False, read_messages=True, read_message_history=True
)
ALLOW_SEND = PermissionOverwrite(
    send_messages=True, read_messages=True, read_message_history=True
)
DISALLOW_READ = discord.PermissionOverwrite(read_messages=False)


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
        if not isinstance(interaction.user, discord.User):
            return
        channel = await self.create_ticket(interaction.user)
        if not channel:
            return await interaction.response.send_message("Failed to create a ticket!")
        await interaction.response.send_message(
            content=f"Ticket has been submitted at: {channel.mention} "
        )
        if self.msg:
            await self.msg.edit(
                content="Thank you for your ticket, staff will be responding as soon as possible",
                view=None,
            )

    async def create_ticket(self, user: discord.User):
        guild = self.bot.get_guild(CONFIG["guild"])
        if not guild:
            return None
        target = guild.get_member(user.id)
        if not target:
            return None
        perms = {
            target: ALLOW_SEND,
            guild.default_role: DISALLOW_READ,
        }
        channel = await guild.create_text_channel(str(user.id), overwrites=perms)  # type: ignore
        self.bot.tickets.update(
            {
                user.id: Ticket(
                    secrets.token_hex(4),
                    user,
                    self.ticket_title.value,  # type: ignore
                    self.content.value,  # type: ignore
                    channel,
                )
            }
        )
        return channel


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

    def cog_check(self, ctx: discord.ApplicationContext | commands.Context):
        if not is_admin(ctx.author):
            return False
        return True

    def is_registered(self, ids: int):
        return self.tickets.get(ids)

    async def delete_ticket(self, ctx: commands.Context):
        try:
            ticket_id = int(ctx.channel.name)
        except ValueError:
            return await ctx.reply("No ticket found!")
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            return await ctx.reply("No ticket found!")
        await ticket.ticket_channel.set_permissions(
            target=ticket.author, overwrite=ALLOW_READ
        )
        await ctx.reply(f"Ticket by {ticket.author} ended!")
        del self.tickets[ticket_id]

    @commands.command("endticket")
    @commands.guild_only()
    async def end_ticket(self, ctx: commands.Context, delete: str = ""):
        await self.delete_ticket(ctx)
        if delete.lower() == "delete":
            await ctx.reply("Deleting this channel in 1 minute")
            await asyncio.sleep(60)
            await ctx.channel.delete()
