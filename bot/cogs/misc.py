from __future__ import annotations
from time import perf_counter

from typing import TYPE_CHECKING
from discord import Cog, option, slash_command
import discord

if TYPE_CHECKING:
    from bot.bot import NhCord


class MiscCog(Cog):
    def __init__(self, bot: NhCord) -> None:
        self.bot = bot

    @slash_command()
    @option(
        "channel", discord.TextChannel, description="Text channel to test permission"
    )
    async def get_perms_channel(
        self, ctx: discord.ApplicationContext, channel: discord.TextChannel
    ):
        if not isinstance(channel, discord.TextChannel):
            return await ctx.respond("Must be text channel")
        perms = channel.permissions_for(ctx.guild.me)
        await ctx.respond(
            f"My permission for {channel.mention}:\n"
            + f"Read History: {perms.read_message_history}\n"
            + f"Manage Channel: {perms.manage_channels}\n"
            + f"Send Message: {perms.send_messages}\n"
            + f"Manage Permission: {perms.manage_permissions}\n"
        )

    @slash_command()
    async def fetch_all_members(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        start = perf_counter()
        bot = 0
        members = 0
        async for member in ctx.guild.fetch_members():
            members += 1
            if member.bot:
                bot += 1
        await ctx.respond(
            f"Fetched {members} server members, {bot} server bots, in {perf_counter() - start}"
        )
