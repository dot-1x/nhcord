from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING

import discord
from discord import Cog, option, slash_command
from discord.commands import ApplicationContext

if TYPE_CHECKING:
    from bot.bot import NhCord


class MiscCog(Cog):
    def __init__(self, bot: NhCord) -> None:
        self.bot = bot

    def cog_check(self, ctx: ApplicationContext) -> bool:
        if not ctx.author.id in self.bot.owner_ids:
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

    @slash_command()
    @option("role", discord.Role, description="Role to check")
    @option(
        "channel",
        discord.TextChannel,
        description="Text channel to check permission for",
    )
    async def get_role_perms(
        self,
        ctx: discord.ApplicationContext,
        role: discord.Role,
        channel: discord.TextChannel,
    ):
        perms = channel.permissions_for(role)
        await ctx.respond(
            f"{role} permission for {channel.mention}:\n"
            + f"Read History: {perms.read_message_history}\n"
            + f"Manage Channel: {perms.manage_channels}\n"
            + f"Send Message: {perms.send_messages}\n"
            + f"Manage Permission: {perms.manage_permissions}\n"
            + f"Manage messages: {perms.manage_messages}\n"
            + f"Manage Roles: {perms.manage_roles}"
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
            f"Fetched {members} members, {bot} bots, in {(perf_counter() - start):.2f}s"
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

    @slash_command()
    @option(name="member", type=discord.Member)
    async def get_user_perms(
        self, ctx: discord.ApplicationContext, member: discord.Member
    ):
        if not await ctx.bot.is_owner(ctx.author):
            return
        perms = member.guild_permissions
        print(dir(perms))
        await ctx.respond(
            f"Manage roles: {perms.manage_roles}\n"
            + f"Move member: {perms.move_members}\n"
            + f"Moderate member: {perms.moderate_members}"
            + f"Manage guild: {perms.manage_guild}",
            ephemeral=True,
        )
