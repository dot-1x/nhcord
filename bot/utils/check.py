import discord
from discord import Member, Role
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
        )
    )


def is_role_admin(role: Role):
    return any(
        (
            role.permissions.manage_messages,
            role.permissions.manage_channels,
            role.permissions.manage_roles,
        )
    )


def admin_check(ctx: commands.Context | discord.ApplicationContext):
    user = ctx.author
    return isinstance(user, Member) and any(
        (
            user.id in CONFIG["owner_ids"],
            user.guild_permissions.administrator,
            user.guild_permissions.manage_messages,
            user.guild_permissions.manage_channels,
            user.guild_permissions.manage_roles,
        )
    )
