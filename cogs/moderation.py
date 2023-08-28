import disnake
from disnake.ext import commands
from core.bot import Nexus
import asyncpg
import datetime
from models.button_view import PageButtons
from typing import Optional
import datetime


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
                "WHERE guild_id = $1 and user_id = $2"
        notes = await self.pool.fetchval(query, ctx.guild.id, user.id)
        if not notes:
            empty_embed = disnake.Embed(title=f"Заметки для пользователя {user.name}", description="Заметок нет",
                                        color=disnake.Color.blurple())
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
        # TODO: добавить кнопку "Просмотреть журнал пользователя"
        time = datetime.datetime.now(datetime.timezone.utc)
        note = f"<t:{int(time.timestamp())}:d>: 💬 **От {ctx.author}:** {note}"

        query = ("INSERT INTO journal (guild_id, user_id, notes) "
                 "VALUES ($1, $2, ARRAY[$3]) "
                 "ON CONFLICT (guild_id, user_id) DO UPDATE "
                 "SET notes = array_append(journal.notes, $3)")
        await self.pool.execute(query, ctx.guild.id,
                                user.id, note)
        embed = disnake.Embed(title="", description=f"Заметка для пользователя {user.mention} добавлена:\n{note}",
                              color=0x74de1d)

        query = ("SELECT channel_id "
                 "FROM journal_logs "
                 "WHERE guild_id = $1")
        channel_id = await self.pool.fetchval(query, ctx.guild.id)
        if channel_id:
            log = disnake.Embed(title="Заметка создана", color=disnake.Color.green(),
                                description=f"{ctx.author.mention} создал заметку о пользователе {user.mention}:\n"
                                            f"{note}")
            log_channel = ctx.guild.get_channel(channel_id)
            await log_channel.send(embed=log)

        await ctx.send(embed=embed, ephemeral=True)

    @journal.sub_command()
    async def edit(self, ctx: disnake.CommandInteraction,
                   user: disnake.User, number: int, note: str):
        """Изменить конкретную заметку о пользователе

        Parameters
        ----------
        ctx: disnake.CommandInteraction
        user: Пользователь
        number: Номер заметки
        note: Новая заметка
        """
        get_note = ("SELECT notes[$3] "
                    "FROM journal "
                    "WHERE guild_id = $1 and user_id = $2")
        old_note = await self.pool.fetchval(get_note, ctx.guild.id,
                                            user.id, number)

        query = ("SELECT notes[$3] "
                 "FROM journal "
                 "WHERE guild_id = $1 and user_id = $2")
        db_note = await self.pool.fetchval(query, ctx.guild.id,
                                           user.id, number)

        note_chunks = db_note.split(" ")
        new_note = f"{' '.join(note_chunks[0:4])} {note} (*изменено*)"

        query = ("UPDATE journal "
                 "SET notes[$3] = $4 "
                 "WHERE guild_id = $1 and user_id = $2")
        await self.pool.execute(query, ctx.guild.id,
                                user.id, number, new_note)

        query = ("SELECT channel_id "
                 "FROM journal_logs "
                 "WHERE guild_id = $1")
        channel_id = await self.pool.fetchval(query, ctx.guild.id)
        if channel_id:
            log = disnake.Embed(title="Заметка изменена", color=disnake.Color.blurple(),
                                description=f"{ctx.author.mention} изменил заметку о пользователе {user.mention}:\n"
                                            f"Старая заметка:\n{old_note}\n"
                                            f"Новая заметка:\n{new_note}")
            log_channel = ctx.guild.get_channel(channel_id)
            await log_channel.send(embed=log)

        await ctx.send("Заметка изменена", ephemeral=True)

    @journal.sub_command()
    async def remove(self, ctx: disnake.CommandInteraction,
                     user: disnake.User, number: int):
        """Удалить заметку/заметки о пользователе

        Parameters
        ----------
        ctx: disnake.CommandInteraction
        user: Пользователь
        number: Номер заметки
        """
        get_note = ("SELECT notes[$3] "
                    "FROM journal "
                    "WHERE guild_id = $1 and user_id = $2")

        delete_note = ("UPDATE journal "
                       "SET notes = array_remove(notes, notes[$3]) "
                       "WHERE guild_id = $1 and user_id = $2")

        note = await self.pool.fetchval(get_note, ctx.guild.id,
                                        user.id, number)
        await self.pool.execute(delete_note, ctx.guild.id,
                                user.id, number)

        query = ("SELECT channel_id "
                 "FROM journal_logs "
                 "WHERE guild_id = $1")
        channel_id = await self.pool.fetchval(query, ctx.guild.id)
        if channel_id:

            log = disnake.Embed(title="Заметка удалена", color=disnake.Color.red(),
                                description=f"{ctx.author.mention} удалил заметку о пользователе {user.mention}:\n"
                                            f"{note}")
            log_channel = ctx.guild.get_channel(channel_id)
            await log_channel.send(embed=log)

        await ctx.send("Список обновлён", ephemeral=True)


def setup(bot):
    bot.add_cog(Journal(bot))
