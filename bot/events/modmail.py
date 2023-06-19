from __future__ import annotations

import asyncio
import secrets
from typing import TYPE_CHECKING

import discord
from discord import Cog, option
from discord.ext import commands
from discord.interactions import Interaction

from ..config import CONFIG
from ..models.modmail.mail import ActiveMail
from ..models.modmail.ticket import Ticket
from ..utils.check import admin_check, is_admin
from ..utils.modmail_utils import ALLOW_READ, CREATE_TICKET_MSG, create_perms_channel

if TYPE_CHECKING:
    from ..bot import NhCord


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
        channel = await create_perms_channel(guild, user)
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


class MailSelectView(discord.ui.View):
    def __init__(self, bot: NhCord, guild: discord.Guild):
        super().__init__(timeout=60, disable_on_timeout=True)
        self.bot = bot
        self.guild = guild
        self.selected: list[discord.TextChannel] = []

    @discord.ui.select(
        discord.ComponentType.channel_select,
        placeholder="Select mail channel",
        max_values=25,
    )
    async def mail_select(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        selected = [
            channel
            for channel in select.values
            if isinstance(channel, discord.TextChannel) and channel.name.isnumeric()
        ]
        await interaction.response.send_message(
            content=f"Selected {len(selected)} text channel", ephemeral=True
        )
        self.selected = selected

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.primary)
    async def confirm(self, _, interaction: discord.Interaction):
        await interaction.response.defer()
        counter = 0
        for channel in self.selected:
            if int(channel.name) in self.bot.mails:
                mail = self.bot.mails.pop(int(channel.name))
                await mail.channel.delete(reason="Purged mail channel")
                del mail
                counter += 1
            elif self.guild.get_member(int(channel.name)):
                await channel.delete(reason="Purged mail channel")
                counter += 1
        self.disable_all_items()
        self.stop()
        await interaction.message.edit(view=self)  # type: ignore
        await interaction.followup.send(f"Deleted {counter} mail channels")


class ModMail(Cog):
    SlashMail = discord.SlashCommandGroup(name="modmail", checks=[admin_check])

    def __init__(self, bot: NhCord) -> None:
        self.bot = bot
        self.enabled = True

    @property
    def tickets(self):
        return self.bot.tickets

    @Cog.listener()
    async def on_message(self, msg: discord.Message):
        author = msg.author
        if author.bot or not self.enabled:
            return

        guild = self.bot.get_guild(CONFIG["guild"])
        if not guild:
            self.enabled = False
            raise ValueError("Guild not found")
        if not guild.get_member(author.id):
            return
        if msg.guild:
            if isinstance(msg.channel, discord.TextChannel):
                try:
                    int(msg.channel.name)
                except ValueError:
                    return
                return await self.listen_mail(msg.channel, msg.content)
            return
        mail = self.check_mail(guild, author)
        if not mail:
            mail = await ActiveMail.create_mail(guild, self.bot, author)
            self.bot.mails.update({author.id: mail})

        urls = [
            file.url for file in msg.attachments if not file.filename.endswith(".exe")
        ]
        await mail.send_log(msg.content, urls)

    async def listen_mail(self, channel: discord.TextChannel, content: str):
        mail = self.bot.mails.get(int(channel.name))
        if not mail:
            author = channel.guild.get_member(int(channel.name))
            if not author:
                return
            mail = ActiveMail.update_mail(self.bot, author, channel)
        await mail.sender.send(content)  # type: ignore

    def cog_check(self, ctx: discord.ApplicationContext | commands.Context):
        if not is_admin(ctx.author):
            return False
        return True

    def is_registered(self, ids: int):
        return self.tickets.get(ids)

    def check_mail(self, guild: discord.Guild, user: discord.User | discord.Member):
        mail = self.bot.mails.get(user.id)
        if mail:
            return mail

        for text in guild.text_channels:
            if text.name == str(user.id):
                mail = ActiveMail.update_mail(self.bot, user, text)
                return mail
        return None

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

    @commands.command("ticekt")
    @commands.dm_only()
    async def start_ticket(self, ctx: commands.Context):
        registered = self.is_registered(ctx.author.id)
        if registered:
            return await ctx.reply(
                f"A ticket already registered on: {registered.ticket_channel.mention}"
            )
        await ctx.reply(
            CREATE_TICKET_MSG.format(author=ctx.author.mention),
            view=TicketView(self.bot),
        )

    @commands.group(name="mm")  # type: ignore
    async def modmail(self, _: commands.Context):
        pass

    @modmail.command("enable")  # type: ignore
    @commands.check(admin_check)
    async def enable_mm(self, ctx: commands.Context):
        self.enabled = True
        await ctx.reply("Modmail Enabled!")

    @modmail.command("disable")  # type: ignore
    @commands.check(admin_check)
    async def disable_mm(self, ctx: commands.Context):
        self.enabled = False
        await ctx.reply("Modmail Disabled!")

    @modmail.command("status")  # type: ignore
    @commands.check(admin_check)
    async def status_mm(self, ctx: commands.Context):
        await ctx.reply(
            f"Modmail status is {'enabled ' if self.enabled else 'disabled'}!"
        )

    @modmail.command("purge")  # type: ignore
    @commands.check(admin_check)
    async def purge_mm(self, ctx: commands.Context):
        mails: list[discord.TextChannel] = []
        for channel in ctx.guild.text_channels:
            try:
                ids = int(channel.name)
            except ValueError:
                continue
            member = ctx.guild.get_member(ids)
            if member:
                mails.append(channel)
        if not mails:
            return await ctx.reply("No mail channel found!")
        await ctx.reply(f"This will purge {len(mails)} mail channel, reply with yes")

        msg = await self.check_response(ctx)
        if msg:
            for channel in mails:
                await channel.delete(reason="Purged mail channel")
                self.bot.mails.clear()
            await msg.reply(f"Succesfully deleted {len(mails)} mail channel")

    @SlashMail.command(name="purge", description="Purge mail channel")
    @option(
        name="all_",
        type=bool,
        defailt=False,
        description="Set whether to delete all or not",
    )
    async def smm_purge(self, ctx: discord.ApplicationContext, all_: bool = False):
        if all_:
            counter = 0
            while self.bot.mails:
                _, mail = self.bot.mails.popitem()
                await mail.channel.delete(reason="Purged mail channel")
                counter += 1
            return await ctx.respond(
                f"Succesfully deleted {counter} mail channel"
                if counter > 0
                else "No mail channel deleted"
            )
        await ctx.respond(view=MailSelectView(self.bot, ctx.guild))

    @SlashMail.command(
        name="delete", description="Delete modmail channel, fill by user or channel"
    )
    @option(name="user", type=discord.Member, description="Sender mail to delete")
    @option(
        name="channel", type=discord.TextChannel, description="Mail channel to delete"
    )
    async def smm_delete(
        self,
        ctx: discord.ApplicationContext,
        user: discord.Member | None = None,
        channel: discord.TextChannel | None = None,
    ):
        mail: ActiveMail | None = None
        if user and channel:
            return await ctx.respond("Fill only by user or channel")
        if user and user.id in self.bot.mails:
            mail = self.bot.mails.pop(user.id)

        if channel and channel.name.isnumeric():
            # check channel name in mails map
            if int(channel.name) in self.bot.mails:
                mail = self.bot.mails.pop(int(channel.name))
            # check by member
            elif ctx.guild.get_member(int(channel.name)):
                mail = ActiveMail(
                    self.bot, ctx.guild.get_member(int(channel.name)), channel
                )
        if not mail:
            return await ctx.respond("Mail not found!")
        await mail.channel.delete(reason="Deleted mail channel")
        await ctx.respond(f"Succesfully deleted mail channel for: {mail.sender}")
        del mail

    async def check_response(self, ctx: commands.Context):
        def check(message: discord.Message):
            return (
                message.author == ctx.author
                and message.channel == ctx.channel
                and message.content.lower() == "yes"
            )

        try:
            msg: discord.Message = await self.bot.wait_for(
                "message",
                check=check,
                timeout=30,
            )
        except asyncio.TimeoutError:
            return None
        return msg
