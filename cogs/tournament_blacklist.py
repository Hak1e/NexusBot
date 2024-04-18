import disnake
from disnake.ext import commands
from core.bot import Nexus
from models.button_view import PageButtons
import asyncpg
from typing import Optional


class Tournament(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool: asyncpg.Pool = self.bot.get_pool()

    @commands.slash_command()
    async def tournament(self, ctx):
        pass

    @tournament.sub_command_group()
    async def blacklist(self, ctx):
        pass

    @blacklist.sub_command()
    async def add(self, ctx: disnake.CommandInteraction,
                  member_or_id: disnake.User, reason: str):
        """Добавить участника в чёрный список

        Parameters
        ----------
        ctx: disnake.CommandInteraction
        member_or_id: Участник сервера. Можно вставить только ID
        reason: Причина добавления в список
        """
        query = "INSERT INTO tournament_blacklist(guild_id, user_id, reason)" \
                "VALUES ($1, $2, $3)" \
                "ON CONFLICT (guild_id, user_id) DO UPDATE " \
                "SET reason = $3"
        await self.pool.execute(query, ctx.guild.id,
                                member_or_id.id, reason)
        await ctx.send(f"{member_or_id.mention} добавлен в чёрный список", ephemeral=True)

    @blacklist.sub_command()
    async def remove(self, ctx: disnake.CommandInteraction,
                     member_or_id: disnake.User):
        """Убрать участника из чёрного списка

        Parameters
        ----------
        ctx: disnake.CommandInteraction
        member_or_id: Участник сервера. Можно вставить только ID
        """
        query = "DELETE FROM tournament_blacklist " \
                "WHERE guild_id = $1 and user_id = $2"
        await self.pool.execute(query, ctx.guild.id,
                                member_or_id.id)
        await ctx.send(f"{member_or_id.name} удалён из чёрного списка", ephemeral=True)

    @blacklist.sub_command()
    async def show(self, ctx: disnake.CommandInteraction,
                   ephemeral: Optional[bool] = True):
        """Показать чёрный список

        Parameters
        ----------
        ctx: disnake.CommandInteraction
        ephemeral: Будет ли ответ видимым только для Вас. True по умолчанию
        """
        query = "SELECT user_id, reason " \
                "FROM tournament_blacklist " \
                "WHERE guild_id = $1"
        blacklist = await self.pool.fetch(query, ctx.guild.id)
        if not blacklist:
            empty_embed = disnake.Embed(title="Чёрный список турнира", description="Список пуст")
            await ctx.send(embed=empty_embed, ephemeral=ephemeral)
            return

        users = [f"<@{value[0]}> (`{value[0]}`)" for value in blacklist]
        reasons = [value[1] for value in blacklist]

        pages = []
        items_per_page = 10
        counter = 1
        for item_index in range(0, len(users), items_per_page):
            page_users = users[item_index:item_index + items_per_page]
            page_reasons = reasons[item_index:item_index + items_per_page]
            page = disnake.Embed(title="Чёрный список турнира")
            for user, reason in zip(page_users, page_reasons):
                page.add_field(name=f"", value=f"{counter}) {user}\n{reason}",
                               inline=False)
                counter += 1
            pages.append(page)

        buttons = PageButtons(pages)
        await ctx.send(embed=pages[0], view=buttons,
                       ephemeral=ephemeral)


def setup(bot):
    bot.add_cog(Tournament(bot))
