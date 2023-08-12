import disnake
from disnake.ext import commands
from core.bot import Nexus
import asyncpg
from typing import Optional


class TournamentButtons(disnake.ui.View):
    def __init__(self, pages, timeout=60):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0

    async def on_timeout(self) -> None:
        self.stop()

    @disnake.ui.button(label="Назад", custom_id="previous_page", style=disnake.ButtonStyle.blurple)
    async def _previous_page(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if self.current_page > 0:
            self.current_page -= 1
            await ctx.response.edit_message(embed=self.pages[self.current_page])
        else:
            await ctx.response.defer()

    @disnake.ui.button(label="Вперёд", custom_id="next_page", style=disnake.ButtonStyle.blurple)
    async def _next_page(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await ctx.response.edit_message(embed=self.pages[self.current_page])
        else:
            await ctx.response.defer()

    @disnake.ui.button(label="Закрыть", custom_id="close", style=disnake.ButtonStyle.red)
    async def _close(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        disabled_buttons = [
            disnake.ui.Button(
                label="Назад",
                style=disnake.ButtonStyle.blurple,
                custom_id="previous_page",
                disabled=True
            ),
            disnake.ui.Button(
                label="Вперёд",
                style=disnake.ButtonStyle.blurple,
                custom_id="next_page",
                disabled=True
            ),
            disnake.ui.Button(
                label="Закрыть",
                style=disnake.ButtonStyle.red,
                custom_id="close",
                disabled=True
            )
        ]
        new_embed = disnake.Embed(title="Чёрный список турнира", description="Список закрыт")
        await ctx.response.edit_message(embed=new_embed, components=disabled_buttons)
        self.stop()


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
    async def add(self, ctx: disnake.CommandInteraction, member_or_id: disnake.User, reason: str):
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
        await self.pool.execute(query, ctx.guild.id, member_or_id.id, reason)
        await ctx.send(f"{member_or_id.name} добавлен в чёрный список", ephemeral=True)

    @blacklist.sub_command()
    async def remove(self, ctx: disnake.CommandInteraction, member_or_id: disnake.User):
        """Убрать участника из чёрного списка
        Parameters
        ----------
        ctx: disnake.CommandInteraction
        member_or_id: Участник сервера. Можно вставить только ID
        """
        query = "DELETE FROM tournament_blacklist " \
                "WHERE guild_id = $1 and user_id = $2"
        await self.pool.execute(query, ctx.guild.id, member_or_id.id)
        await ctx.send(f"{member_or_id.name} удалён из чёрного списка", ephemeral=True)

    @blacklist.sub_command()
    async def show(self, ctx: disnake.CommandInteraction, ephemeral: Optional[bool] = True):
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

        users = [f"<@{value[0]}> (`{value[0]}`)" for value in blacklist]
        reasons = [value[1] for value in blacklist]

        pages = []
        items_per_page = 10
        counter = 1
        for i in range(0, len(users), items_per_page):
            page_users = users[i:i+items_per_page]
            page_reasons = reasons[i:i+items_per_page]
            page = disnake.Embed(title="Чёрный список турнира")
            for user, reason in zip(page_users, page_reasons):
                page.add_field(f"", f"{counter}) {user}\n{reason}", inline=False)
                counter += 1
            pages.append(page)

        buttons = TournamentButtons(pages)
        if len(pages) > 0:
            await ctx.send(embed=pages[0], view=buttons, ephemeral=ephemeral)
        else:
            empty_embed = disnake.Embed(title="Чёрный список турнира", description="Список пуст")
            await ctx.send(embed=empty_embed, ephemeral=ephemeral)



def setup(bot):
    bot.add_cog(Tournament(bot))

