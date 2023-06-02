from __future__ import annotations
from time import perf_counter

from typing import TYPE_CHECKING
from discord import Cog, option, slash_command
import discord
from discord.commands import ApplicationContext

if TYPE_CHECKING:
    from bot.bot import NhCord


class MiscCog(Cog):
    def __init__(self, bot: NhCord) -> None:
        self.bot = bot

    def cog_check(self, ctx: ApplicationContext) -> bool:
        if not ctx.author.id in [732842920889286687]:
            return False
        return True

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

    @slash_command(
        description="This will call discord API and fetch all members on current guild"
    )
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
            f"Fetched {members} server members, {bot} server bots, in {(perf_counter() - start):.2f}s"
        )

    @slash_command()
    async def cached_members(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        start = perf_counter()
        count = 0
        bot = 0
        for member in ctx.guild.members:
            count += 1
            if member.bot:
                bot += 1
        await ctx.respond(
            f"Cached {count} server members, {bot} server bots, in {(perf_counter() - start):.2f}s"
        )
