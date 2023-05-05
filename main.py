import os

from dotenv import load_dotenv
from bot import NhCord


if __name__ == "__main__":
    load_dotenv()
    bot = NhCord()
    bot.run(os.getenv("DCTOKEN"))
