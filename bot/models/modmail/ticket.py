from dataclasses import dataclass, field
from datetime import datetime

import discord


@dataclass
class Ticket:
    ticket_id: str
    author: discord.User
    title: str
    content: str
    ticket_channel: discord.TextChannel

    is_done: bool = False
    created_at: datetime = field(default=datetime.now())


@dataclass
class Mail:
    sender: discord.User | discord.Member
    content: str
