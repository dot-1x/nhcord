import discord

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


async def get_category(guild: discord.Guild):
    categ: discord.CategoryChannel
    perm_role = [role for role in guild.roles if is_role_admin(role)]
    for category in guild.categories:
        if category.name == "ModMail":
            categ = category
            break
    else:
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
    guild: discord.Guild, user: discord.User | discord.Member
):
    target = guild.get_member(user.id)
    if not target:
        return None
    categ = await get_category(guild)
    perms = {
        target: ALLOW_SEND,
        guild.default_role: DISALLOW_READ,
        guild.me: ALLOW_SEND,
    }
    channel = await guild.create_text_channel(
        str(user.id), overwrites=perms, category=categ  # type: ignore
    )
    return channel
