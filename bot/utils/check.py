from discord import Member


def is_admin(user: Member):
    if user.id in [732842920889286687]:
        return True
    return any(
        (
            user.guild_permissions.manage_messages,
            user.guild_permissions.manage_channels,
            user.guild_permissions.manage_roles,
            user.guild_permissions.manage_guild,
        )
    )
