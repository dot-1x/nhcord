import discord


class RequiredPermissionError(discord.ClientException):
    """Exception when bot needs certain permission"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)
