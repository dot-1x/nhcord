from discord import Member


def is_admin(user: Member):
    return any(
        (
            user.guild_permissions.manage_messages,
            user.guild_permissions.manage_channels,
            user.guild_permissions.manage_roles,
            user.guild_permissions.manage_guild,
        )
    )
