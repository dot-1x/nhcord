from PIL import Image
from discord import Guild, Role

TIMELEFT = "Timeleft: <t:{time}:R>\n"
WIDTH, HEIGHT = (160, 120)
black = Image.new("RGB", (WIDTH, HEIGHT))
broken = Image.open("bot/glass_broken.jpg").resize((WIDTH, HEIGHT))
safe = Image.open("bot/glass_safe.jpg").resize((WIDTH, HEIGHT))


def create_image_grid(revealed: list[int], safepos: int):
    rows = 2
    cols = 2
    grid = Image.new("RGB", size=(cols * WIDTH, rows * HEIGHT))
    for idx in range(4):
        if idx in revealed:
            grid.paste(
                broken if idx != safepos else safe,
                box=(idx % cols * WIDTH, idx // cols * HEIGHT),
            )
            continue
        grid.paste(black, box=(idx % cols * WIDTH, idx // cols * HEIGHT))
    return grid


async def get_member_by_role(guild: Guild, role: Role, role_except: Role | None):
    """Fetch all members then check they have one of required roles and exception role

    Args:
        guild (Guild): guild members to check
        roles Role: required roles
        roles_except Role | None: exception role

    Yields:
        discord.Member: founded member
    """
    for member in guild.members:
        if (
            member.get_role(role.id)
            and (not member.get_role(role_except.id) if role_except else True)
            and not member.bot
        ):
            yield member
