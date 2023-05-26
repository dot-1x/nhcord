import os

import httpx
from dotenv import load_dotenv
from bot import NhCord

# pylint: disable=line-too-long
BROKEN_IMG = "https://plus.unsplash.com/premium_photo-1675526090845-a8b982cabae6?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxzZWFyY2h8MXx8YnJva2VuJTIwZ2xhc3N8ZW58MHx8MHx8&w=1000&q=80"
SAFE_IMG = "https://st3.depositphotos.com/1031174/15354/i/600/depositphotos_153541450-stock-photo-glass-texture-background.jpg"

if __name__ == "__main__":
    load_dotenv()
    with open("bot/glass_broken.jpg", "wb") as file:
        resp = httpx.get(BROKEN_IMG)
        file.write(resp.read())
    with open("bot/glass_safe.jpg", "wb") as file:
        resp = httpx.get(SAFE_IMG)
        file.write(resp.read())

    bot = NhCord()
    bot.run(os.getenv("LIVETOKEN"))
