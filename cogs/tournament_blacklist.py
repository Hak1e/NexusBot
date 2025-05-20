import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands
from core.bot import Nexus
from models.button_view import PageButtons
import asyncpg
from typing import Optional


class Tournament(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool: asyncpg.Pool = self.bot.get_pool()

    tournament = SlashCommandGroup("tournament")
    blacklist = tournament.create_subgroup("blacklist")

    @blacklist.command()
    async def add(
        self, ctx: discord.ApplicationContext, member_or_id: discord.User, reason: str
    ):
        """Добавить участника в чёрный список

        Parameters
        ----------
        ctx: discord.ApplicationContext
        member_or_id: Участник сервера. Можно вставить только ID
        reason: Причина добавления в список
        """
        query = (
            "INSERT INTO tournament_blacklist(guild_id, user_id, reason)"
            "VALUES ($1, $2, $3)"
            "ON CONFLICT (guild_id, user_id) DO UPDATE "
            "SET reason = $3"
        )
        await self.pool.execute(query, ctx.guild.id, member_or_id.id, reason)
        await ctx.respond(
            f"{member_or_id.mention} добавлен в чёрный список", ephemeral=True
        )

    @blacklist.command()
    async def remove(self, ctx: discord.ApplicationContext, member_or_id: discord.User):
        """Убрать участника из чёрного списка

        Parameters
        ----------
        ctx: discord.ApplicationContext
        member_or_id: Участник сервера. Можно вставить только ID
        """
        query = (
            "DELETE FROM tournament_blacklist " "WHERE guild_id = $1 and user_id = $2"
        )
        await self.pool.execute(query, ctx.guild.id, member_or_id.id)
        await ctx.respond(
            f"{member_or_id.name} удалён из чёрного списка", ephemeral=True
        )

    @blacklist.command()
    async def show(
        self, ctx: discord.ApplicationContext, ephemeral: Optional[bool] = True
    ):
        """Показать чёрный список

        Parameters
        ----------
        ctx: discord.ApplicationContext
        ephemeral: Будет ли ответ видимым только для Вас. True по умолчанию
        """
        query = (
            "SELECT user_id, reason " "FROM tournament_blacklist " "WHERE guild_id = $1"
        )
        blacklist = await self.pool.fetch(query, ctx.guild.id)
        if not blacklist:
            empty_embed = discord.Embed(
                title="Чёрный список турнира", description="Список пуст"
            )
            await ctx.respond(embed=empty_embed, ephemeral=ephemeral)
            return

        users = [f"<@{value[0]}> (`{value[0]}`)" for value in blacklist]
        reasons = [value[1] for value in blacklist]

        pages = []
        items_per_page = 10
        counter = 1
        for item_index in range(0, len(users), items_per_page):
            page_users = users[item_index : item_index + items_per_page]
            page_reasons = reasons[item_index : item_index + items_per_page]
            page = discord.Embed(title="Чёрный список турнира")
            for user, reason in zip(page_users, page_reasons):
                page.add_field(
                    name=f"", value=f"{counter}) {user}\n{reason}", inline=False
                )
                counter += 1
            pages.append(page)

        buttons = PageButtons(pages)
        await ctx.respond(embed=pages[0], view=buttons, ephemeral=ephemeral)


def setup(bot):
    bot.add_cog(Tournament(bot))
