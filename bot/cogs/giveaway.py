from __future__ import annotations
import asyncio
from datetime import datetime, timedelta
from random import randrange, shuffle

from typing import TYPE_CHECKING
import discord
from discord import (
    Cog,
    option,
)

from discord.ui import View, button
from discord.ext import commands

if TYPE_CHECKING:
    from ..bot import NhCord


async def get_users_data(bot: NhCord, ids: list[int]):
    channel = bot.get_channel(1097850451589865522)
    if not isinstance(channel, discord.TextChannel):
        raise ValueError("Text channel not found!")
    async for msg in channel.history(oldest_first=True, limit=None):
        if msg.author.id in ids and msg.author:
            yield msg


class GiveawayView(View):
    def __init__(
        self,
        bot: NhCord,
        winners: int,
        role: discord.Role | None,
        timeout: float,
        deadline: datetime,
    ):
        super().__init__(timeout=timeout + 60 * 60 * 2, disable_on_timeout=True)
        self.role = role
        self.participants: list[discord.Member] = []
        self.winners: list[discord.Member] = []
        self.total_paarticipants = 0
        self.ended = False
        self.max_winner = winners
        self.bot = bot
        self.deadline = deadline

    @button(label="participate", style=discord.ButtonStyle.primary)
    async def participate(self, _, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            return
        if (
            self.role
            and isinstance(interaction.user, discord.Member)
            and interaction.user.get_role(self.role.id) is None
        ):
            return await interaction.response.send_message(
                "Does not met role requirement", ephemeral=True
            )
        if interaction.user in self.participants:
            return await interaction.response.send_message(
                "Already participated", ephemeral=True
            )
        self.participants.append(interaction.user)
        await interaction.response.send_message(
            "Succesfully participated", ephemeral=True
        )
        self.total_paarticipants += 1

    @button(label="Reroll", style=discord.ButtonStyle.success)
    async def reroll(self, _, interaction: discord.Interaction):
        if not interaction.user:
            return
        if not isinstance(interaction.channel, discord.TextChannel):
            return
        perms = interaction.channel.permissions_for(interaction.user)  # type: ignore
        if (
            not perms.manage_channels
            or not perms.manage_messages
            or not perms.manage_guild
        ):
            return await interaction.response.send_message(
                "This button is not for you!", ephemeral=True
            )
        if not self.ended:
            return await interaction.response.send_message(
                "Giveaway is still running", ephemeral=True
            )
        select: discord.ui.Select[GiveawayView] = discord.ui.Select(
            discord.ComponentType.user_select,
            placeholder="Select user to reroll",
            options=[
                discord.SelectOption(label=winner.name, value=str(winner.id))
                for winner in self.winners
            ],
        )
        select.callback = self.reroll_action  # type: ignore
        view = View(select)
        await interaction.response.send_message(view=view, ephemeral=True)

    async def reroll_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("selected", ephemeral=True)

    async def start_timer(self):
        if not self.message:
            raise ValueError("Message not found!")
        self.bot.log.info("Starting giveaway timer!")
        while datetime.now() < self.deadline:
            await asyncio.sleep(1)
        await self.roll()

    async def roll(self):
        if not self.message:
            raise ValueError("Message not found!")
        self.ended = True
        embed = self.message.embeds[0]
        if self.total_paarticipants < 1:
            self.disable_all_items()
            embed.description = "No participants"
            return await self.message.edit(view=self, embed=embed)
        for children in self.children:
            if (
                isinstance(children, discord.ui.Button)
                and children.label == "participate"
            ):
                participate_btn = children
                break
        else:
            return self.disable_all_items()
        participate_btn.disabled = True
        shuffle(self.participants)
        winners = [
            self.participants.pop(randrange(len(self.participants)))
            for _ in range(min(self.max_winner, self.total_paarticipants))
        ]
        winner_map: dict[int, list[discord.Message]] = {}
        async for message in get_users_data(
            self.bot, [winner.id for winner in winners]
        ):
            if not message:
                continue
            if message.author.id not in winner_map:
                winner_map.update({message.author.id: []})
            winner_map[message.author.id].append(message.jump_url)
        embed.description = "Winners:\n" + "\n".join(
            f"{winner.mention}: {winner_map[winner.id]}" for winner in winners
        )
        self.winners = winners
        print("Edited succesfully")
        await self.message.edit(view=self, embed=embed)


class GiveawayCog(Cog):
    def __init__(self, bot: NhCord) -> None:
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
                discord.EmbedField(
                    name="Author",
                    value=ctx.author.mention if not author else author.mention,
                    inline=True,
                ),
                discord.EmbedField(name="Reward", value=reward, inline=True),
                discord.EmbedField(name="Max Winner", value=str(winners), inline=True),
                discord.EmbedField(
                    name="Role", value=role.mention if role else "None", inline=True
                ),
                discord.EmbedField(name="Timeleft", value=deadline_str, inline=True),
            ],
        )
        view = GiveawayView(
            self.bot, winners, role, deltatime.total_seconds(), deadline
        )
        await ctx.response.send_message(
            f"{role.mention if role else '@everyone'}" if tag else None,
            embed=embed,
            view=view,
        )
        await view.start_timer()