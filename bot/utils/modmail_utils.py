import discord
from bot.logs.custom_logger import BotLogger

from bot.utils.check import is_role_admin

CREATE_TICKET_MSG = "Hello {author}, to contact our discord staff,\
please fill form by clicking button below"
ALLOW_READ = discord.PermissionOverwrite(
    send_messages=False, read_messages=True, read_message_history=True
)
ALLOW_SEND = discord.PermissionOverwrite(
    send_messages=True, read_messages=True, read_message_history=True
)
DISALLOW_READ = discord.PermissionOverwrite(read_messages=False)
ALLOW_EDIT = discord.PermissionOverwrite(
    send_messages=False,
    read_messages=True,
    read_message_history=True,
    manage_channels=True,
)
_log = BotLogger("[MODMAIL]")


async def get_category(guild: discord.Guild):
    for category in guild.categories:
        if category.name == "ModMail":
            return category
    perm_role = [role for role in guild.roles if is_role_admin(role)]
    _log.info("Allowed role is %s", perm_role)
    categ = await guild.create_category(
        name="ModMail",
        overwrites={
            guild.default_role: DISALLOW_READ,
            guild.me: ALLOW_SEND,
            **{role: ALLOW_SEND for role in perm_role},
        },
    )
    return categ


async def create_perms_channel(
    guild: discord.Guild, user: discord.User | discord.Member, allow_target=False
):
    target = guild.get_member(user.id)
    if not target:
        raise ValueError("Member not found!")
    categ = await get_category(guild)
    channel = await guild.create_text_channel(
        str(user.id), category=categ  # type: ignore
    )
    if allow_target:
        await channel.set_permissions(target, overwrite=ALLOW_SEND)
    return channel
