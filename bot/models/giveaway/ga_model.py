from __future__ import annotations

import asyncio
from datetime import datetime
from random import randrange, shuffle
from typing import TYPE_CHECKING

import discord
from discord.ui import View, button

from ...logs.custom_logger import BotLogger

if TYPE_CHECKING:
    from ...bot import NhCord

_log = BotLogger("[GIVEAWAY]")


async def get_users_data(bot: NhCord, ids: list[int]):
    channel = bot.get_channel(1097850451589865522)
    if not isinstance(channel, discord.TextChannel):
        raise ValueError("Text channel not found!")
    async for msg in channel.history(oldest_first=True, limit=None):
        if msg.author.id in ids:
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
        self.reroll_select: discord.ui.Select[GiveawayView] = discord.ui.Select(
            discord.ComponentType.string_select,
            placeholder="Select user to reroll",
        )

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

    @button(label="reroll", style=discord.ButtonStyle.success)
    async def reroll(self, _, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            return
        if not self.ended:
            return await interaction.response.send_message(
                "Giveaway is still running", ephemeral=True
            )
        if not self.participants:
            return await interaction.response.send_message(
                "Insufficient participants to reroll!", ephemeral=True
            )
        self.reroll_select.options = [
            discord.SelectOption(label=str(winner), value=str(winner.id))
            for winner in self.winners
        ]
        self.reroll_select.callback = self.reroll_action  # type: ignore
        view = View(self.reroll_select)
        await interaction.response.send_message(
            "select user to reroll", view=view, ephemeral=True
        )

    @button(label="participants: 0", style=discord.ButtonStyle.gray)
    async def participant_btn(self, _, interaction: discord.Interaction):
        if not interaction.user in self.participants:
            return await interaction.response.send_message(
                "You have not participated", ephemeral=True
            )
        await interaction.response.send_message(
            f"You have participated among {self.total_paarticipants} participants",
            ephemeral=True,
        )

    async def get_winners(self):
        if not self.message:
            raise ValueError("Message not found!")
        self.ended = True
        embed = self.message.embeds[0]
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
        return winners, embed

    async def reroll_action(self, interaction: discord.Interaction):
        await interaction.response.send_message("selected", ephemeral=True)
        print(self.reroll_select.values)

    async def start_timer(self):
        if not self.message:
            raise ValueError("Message not found!")
        asyncio.create_task(self.reload_participants())
        _log.info("Starting giveaway timer!")
        while datetime.now() < self.deadline:
            await asyncio.sleep(1)
        await self.roll()

    async def reload_participants(self):
        for children in self.children:
            if (
                isinstance(children, discord.ui.Button)
                and children.label is not None
                and "participants:" in children.label
            ):
                total_entries_btn = children
                break
        else:
            return
        while not self.ended:
            total_entries_btn.label = f"Participants: {self.total_paarticipants}"
            await self.message.edit(view=self)
            await asyncio.sleep(10)

    async def roll(self, to_reroll: None | list[int] = None):
        if to_reroll:
            return
        if not self.message:
            raise ValueError("Message not found!")
        self.ended = True
        embed = self.message.embeds[0]
        if self.total_paarticipants < 1:
            self.disable_all_items()
            embed.description = "No participants"
            _log.warning("Giveaway ended with no participant")
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

        try:
            self.winners, embed = await self.get_winners()
        except discord.Forbidden:
            await self.message.edit(view=self)
            return await self.message.reply("I cannot read data channel")
        await self.message.edit(view=self, embed=embed)
        mentions = ", ".join(winner.mention for winner in self.winners)
        await self.message.reply(
            f"Congratulations {mentions} you have won the Giveaway"
        )
