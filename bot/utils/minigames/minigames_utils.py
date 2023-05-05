from random import shuffle
from PIL import Image, ImageFilter


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
