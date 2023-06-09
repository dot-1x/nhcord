from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import discord
from discord import option
from discord.ext import commands

from ...logs.custom_logger import BotLogger
from ...models.giveaway import GiveawayView
from .admin import AdminCog

if TYPE_CHECKING:
    from ...bot import NhCord

_log = BotLogger("[GIVEAWAY]")


class GiveawayCog(AdminCog):
    def __init__(self, bot: NhCord) -> None:
        super().__init__(bot)
        self.bot = bot

    @commands.slash_command()
    @option(name="name", type=str, description="Set giveaway name")
    @option("reward", type=str, description="Set for reward")
    @option("winners", type=int, description="Set maximum winner")
    @option("timer", type=str, description="Set Giveaway timer (HH-MM-SS): (01:30:00)")
    @option("role", type=discord.Role, description="Set allowed role", required=False)
    @option("tag", type=bool, description="Set whether to tag or not")
    @option("author", type=discord.Member, description="Set giveaway author")
    async def giveaway(
        self,
        ctx: discord.ApplicationContext,
        name: str,
        reward: str,
        winners: int,
        timer: str,
        role: discord.Role | None = None,
        tag: bool = False,
        author: discord.Member | None = None,
    ):
        try:
            timelimit = datetime.strptime(timer, "%H:%M:%S")
        except ValueError:
            return await ctx.respond(
                "Invalid time format\n"
                + "format should be (HH:MM:SS)\n"
                + "example: 01:30:00 (an hour and half)"
            )
        deltatime = timedelta(
            seconds=timelimit.second, minutes=timelimit.minute, hours=timelimit.hour
        )
        if deltatime.total_seconds() < 10:
            return await ctx.respond("Time cannot be lower than 10 seconds")
        deadline = datetime.now() + deltatime
        deadline_str = f"<t:{deadline.timestamp():.0f}:R>"
        embed = discord.Embed(
            title=name,
            description="Click participate to enter!!!",
            color=discord.Color.nitro_pink(),
            fields=[
                discord.EmbedField(name="Reward", value=reward, inline=False),
                discord.EmbedField(
                    name="Author",
                    value=ctx.author.mention if not author else author.mention,
                    inline=True,
                ),
                discord.EmbedField(name="Winners", value=str(winners), inline=True),
                discord.EmbedField(
                    name="Role", value=role.mention if role else "None", inline=True
                ),
                discord.EmbedField(name="Timeleft", value=deadline_str, inline=True),
            ],
            timestamp=datetime.now(),
        )
        view = GiveawayView(
            self.bot, winners, role, deltatime.total_seconds(), deadline
        )
        await ctx.response.send_message(
            f"{role.mention if role else '@everyone'}" if tag else None,
            embed=embed,
            view=view,
        )
        _log.info("Giveaway created at %f", datetime.now().timestamp())
        await view.start_timer()
