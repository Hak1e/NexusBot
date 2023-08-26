import disnake
from disnake.ext import commands
from core.bot import Nexus
import asyncpg
import datetime
from models.button_view import PageButtons
from typing import Optional


class Journal(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool: asyncpg.Pool = self.bot.get_pool()

    @commands.slash_command()
    async def journal(self, ctx):
        pass

    @journal.sub_command()
    async def show(self, ctx: disnake.CommandInteraction,
                   user: disnake.User, ephemeral: Optional[bool] = False):
        """Показать журнал пользователя

        Parameters
        ----------
        ctx: disnake.CommandInteraction
        user: Пользователь
        ephemeral: Отправить эфемерное сообщение. По стандарту False
        """

        query = "SELECT notes " \
                "FROM journal " \
                "WHERE user_id = $1 and guild_id = $2"
        notes = await self.pool.fetchval(query, user.id, ctx.guild.id)
        if not notes:
            empty_embed = disnake.Embed(title=f"Заметки для пользователя {user.name}", description="Заметок нет")
            await ctx.send(embed=empty_embed, ephemeral=ephemeral)
            return

        pages = []
        items_per_page = 10
        counter = 1
        for item_index in range(0, len(notes), items_per_page):
            page_notes = notes[item_index:item_index + items_per_page]
            page = disnake.Embed(title=f"Заметки для пользователя {user.name}", color=0x55bd00)
            for note in page_notes:
                page.add_field(name="", value=f"`#{counter}` {note}",
                               inline=False)
                counter += 1
            pages.append(page)

        buttons = PageButtons(pages)
        await ctx.send(embed=pages[0], view=buttons,
                       ephemeral=ephemeral)

    @journal.sub_command()
    async def add(self, ctx: disnake.CommandInteraction,
                  user: disnake.User, note: str):
        """Добавить пользователя в журнал

        Parameters
        ----------
        ctx: disnake.CommandInteraction
        user: Пользователь
        note: Заметка о пользователе
        """

        query = ("INSERT INTO journal (user_id, guild_id, notes) "
                 "VALUES ($1, $2, ARRAY[$3]) "
                 "ON CONFLICT (user_id, guild_id) DO UPDATE "
                 "SET notes = array_append(journal.notes, $3)")
        await self.pool.execute(query, user.id,
                                ctx.guild.id, note)
        embed = disnake.Embed(title="", description=f"Заметка для пользователя {user.mention} добавлена:\n`{note}`",
                              color=0x74de1d)
        await ctx.send(embed=embed, ephemeral=True)

    @journal.sub_command()
    async def remove(self, ctx: disnake.CommandInteraction,
                     user: disnake.User, numbers: str):
        """Удалить конкретную заметку о пользователе

        Parameters
        ----------
        ctx: disnake.CommandInteraction
        user: Пользователь
        numbers: Номер заметки через пробел
        """
        query = ("UPDATE journal "
                 "SET notes = array_remove(notes, notes[$3]) "
                 "WHERE user_id = $1 and guild_id = $2")

        for number in numbers.split():
            await self.pool.execute(query, user.id, ctx.guild.id, int(number))

        await ctx.send("Список обновлён", ephemeral=True)


def setup(bot):
    bot.add_cog(Journal(bot))
