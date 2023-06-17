from discord import Member
import discord
from discord.ext import commands


from ..config import CONFIG


def is_admin(user: Member):
    return any(
        (
            user.id in CONFIG["owner_ids"],
            user.guild_permissions.administrator,
            user.guild_permissions.manage_messages,
            user.guild_permissions.manage_channels,
            user.guild_permissions.manage_roles,
            user.guild_permissions.manage_guild,
        )
    )


def admin_check(ctx: commands.Context | discord.ApplicationContext):
    user = ctx.author
    return any(
        (
            user.id in CONFIG["owner_ids"],
            user.guild_permissions.administrator,
            user.guild_permissions.manage_messages,
            user.guild_permissions.manage_channels,
            user.guild_permissions.manage_roles,
            user.guild_permissions.manage_guild,
        )
    )
