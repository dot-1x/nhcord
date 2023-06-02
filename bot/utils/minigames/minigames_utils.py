from random import shuffle
from PIL import Image, ImageFilter
from discord import Guild, Role


def create_image_grid():
    broken = Image.open("bot/glass_broken.jpg")
    broken = broken.resize((160, 120))
    broken_blurry = broken.filter(ImageFilter.BoxBlur(4))
    safe = Image.open("bot/glass_safe.jpg")
    safe = safe.resize((160, 120))
    safe_blurry = safe.filter(ImageFilter.BoxBlur(4))
    rows = 2
    cols = 2
    width, height = broken_blurry.size
    grid = Image.new("RGB", size=(cols * width, rows * height))
    images = [broken_blurry, broken_blurry, broken_blurry, safe_blurry]
    shuffle(images)
    safe_point = 0
    for i, img in enumerate(images):
        grid.paste(img, box=(i % cols * width, i // cols * height))
        if img is safe_blurry:
            safe_point = i
    return grid, safe_point


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
