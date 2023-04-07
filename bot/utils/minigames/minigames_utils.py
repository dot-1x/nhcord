from random import shuffle
from PIL import Image, ImageFilter


def create_image_grid():
    img = Image.open("bot/glass_break.jpg")
    blurry = img.filter(ImageFilter.GaussianBlur(100))
    rows = 2
    cols = 2
    w, h = blurry.size
    grid = Image.new("RGB", size=(cols * w, rows * h))
    images = [blurry, blurry, blurry, img]
    shuffle(images)
    safe_point = 0
    for i, img_ in enumerate(images):
        grid.paste(img_, box=(i % cols * w, i // cols * h))
        if img_ is img:
            safe_point = i
    return grid, safe_point
