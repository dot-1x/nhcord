from dataclasses import dataclass

import discord


@dataclass
class Ticket:
    ticket_id: str
    author: discord.User
    title: str
    content: str
    ticket_channel: discord.TextChannel

    is_done: bool = False
