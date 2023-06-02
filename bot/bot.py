from discord import Intents
from discord.ext import commands

from .logs import BotLogger


class NhCord(commands.Bot):
    def __init__(self, *args, **options):
        intent = Intents()
        intent.members = True
        intent.guilds = True
        intent.message_content = True
        intent.guild_messages = True
        super().__init__(".", intents=intent, *args, **options)
        self.log = BotLogger("[BOT]")
        self.load_extension(".cogs", package="bot", recursive=False, store=False)

    async def on_ready(self):
        self.log.info("Bot is ready!")
