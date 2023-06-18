from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import discord

from bot.logs.custom_logger import MailLogger
from bot.utils.modmail_utils import get_category, DISALLOW_READ, ALLOW_SEND

if TYPE_CHECKING:
    from bot.bot import NhCord


@dataclass
class ActiveMail:
    bot: NhCord
    sender: discord.User | discord.Member
    channel: discord.TextChannel
    log: MailLogger | None = None

    async def send_log(self, content: str, file_urls: list[str]):
        if not self.log:
            self.log = MailLogger(self.sender.name)
        urls = "\n".join(file_urls)
        emb = discord.Embed(
            description=f"{content}",
            colour=discord.Colour.green(),
            timestamp=datetime.now(),
        )
        emb.set_author(name=self.sender.name, icon_url=self.sender.display_avatar.url)
        if content:
            await self.channel.send(embed=emb)
            self.log.info(content)
        if file_urls:
            emb.description = urls
            await self.channel.send(embed=emb)
            self.log.info("Send an attachment file:\n%s", urls)

    @classmethod
    async def create_mail(
        cls,
        guild: discord.Guild,
        bot: NhCord,
        sender: discord.User | discord.Member,
    ):
        categ = await get_category(guild)
        member = guild.get_member(732842920889286687)
        overwrite: dict[discord.Member | discord.Role, discord.PermissionOverwrite] = {
            guild.default_role: DISALLOW_READ,
            guild.me: ALLOW_SEND,
        }
        if member:
            overwrite.update({member: ALLOW_SEND})
            channel = await guild.create_text_channel(
                str(sender.id), category=categ, overwrites=overwrite
            )
        return cls(bot, sender, channel)
