import disnake
from disnake.ext import commands
from core.bot import Nexus
import asyncpg
from models.button_view import PageButtons
from typing import Optional
import datetime


class Journal(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool: asyncpg.Pool = self.bot.get_pool()

    @commands.slash_command()
    async def journal_show(self, ctx: disnake.CommandInteraction,
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
            buttons = PageButtons([])
            await ctx.send(embed=empty_embed, ephemeral=ephemeral,
                           view=buttons)
            return

        pages = []
        items_per_page = 10
        counter = 1
        for item_index in range(0, len(notes), items_per_page):
            page_notes = notes[item_index:item_index + items_per_page]
            page = disnake.Embed(title=f"Заметки для пользователя {user.name}", color=disnake.Color.blurple())
            for note in page_notes:
                page.add_field(name="", value=f"`#{counter}` {note}",
                               inline=False)
                counter += 1
            pages.append(page)

        buttons = PageButtons(pages)
        await ctx.send(embed=pages[0], view=buttons,
                       ephemeral=ephemeral)

    @commands.slash_command()
    async def journal_add(self, ctx: disnake.CommandInteraction,
                          user: disnake.User, note: str):
        """Добавить пользователя в журнал

        Parameters
        ----------
        ctx: disnake.CommandInteraction
        user: Пользователь
        note: Заметка о пользователе
        """
        time = datetime.datetime.now(datetime.timezone.utc)
        note = f"<t:{int(time.timestamp())}:d>: 💬 **От <@{ctx.author.id}>:** {note}"
        query = ("INSERT INTO journal (guild_id, user_id, notes) "
                 "VALUES ($1, $2, ARRAY[$3]) "
                 "ON CONFLICT (guild_id, user_id) DO UPDATE "
                 "SET notes = array_append(journal.notes, $3)")
        await self.pool.execute(query, ctx.guild.id,
                                user.id, note)

        query = ("SELECT channel_id "
                 "FROM journal_logs "
                 "WHERE guild_id = $1")
        channel_id = await self.pool.fetchval(query, ctx.guild.id)
        if channel_id:
            log = disnake.Embed(title="Заметка создана", color=disnake.Color.green(),
                                description=f"{ctx.author.mention} создал(а) заметку о пользователе {user.mention}:\n"
                                            f"{note}")
            log_channel = ctx.guild.get_channel(channel_id)
            await log_channel.send(embed=log)

        embed = disnake.Embed(title="", description=f"Заметка для пользователя {user.mention} добавлена:\n{note}",
                              color=disnake.Color.green())
        await ctx.send(embed=embed, ephemeral=True)

    @commands.slash_command()
    async def journal_edit(self, ctx: disnake.CommandInteraction,
                           user: disnake.User, number: int,
                           note: str):
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
                                description=f"{ctx.author.mention} изменил(а) заметку о пользователе {user.mention}:\n"
                                            f"Старая заметка:\n{old_note}\n"
                                            f"Новая заметка:\n{new_note}")
            log_channel = ctx.guild.get_channel(channel_id)
            await log_channel.send(embed=log)

        embed = disnake.Embed(title="", description=f"Заметка для пользователя {user.mention} изменена:\n"
                                                    f"Старая заметка:\n{old_note}\n"
                                                    f"Новая заметка:\n{new_note}",
                              color=disnake.Color.green())
        await ctx.send(embed=embed, ephemeral=True)

    @commands.slash_command()
    async def journal_remove(self, ctx: disnake.CommandInteraction,
                             user: disnake.User, numbers: str):
        """Удалить заметку/заметки о пользователе

        Parameters
        ----------
        ctx: disnake.CommandInteraction
        user: Пользователь
        numbers: Номер заметки через пробел
        """
        notes_number = [f"`#{number}`" for number in numbers.split()]

        get_notes = ("SELECT notes "
                     "FROM journal "
                     "WHERE guild_id = $1 and user_id = $2")
        notes = await self.pool.fetchval(get_notes, ctx.guild.id, user.id)
        indexes = list(map(int, numbers.split()))
        indexes = [number - 1 for number in indexes]
        new_notes = []
        deleted_notes = []
        for index, note in enumerate(notes):
            if index not in indexes:
                new_notes.append(note)
            else:
                deleted_notes.append(note)

        update_notes = ("UPDATE journal "
                        "SET notes = $3 "
                        "WHERE guild_id = $1 and user_id = $2")
        await self.pool.execute(update_notes, ctx.guild.id, user.id, new_notes)

        query = ("SELECT channel_id "
                 "FROM journal_logs "
                 "WHERE guild_id = $1")
        channel_id = await self.pool.fetchval(query, ctx.guild.id)
        if channel_id:
            log = disnake.Embed(title="Заметка удалена", color=disnake.Color.red(),
                                description=f"{ctx.author.mention} удалил(а) заметку {' '.join(notes_number)} "
                                            f"о пользователе {user.mention}:\n")
            log.add_field(name="", value="\n".join(deleted_notes))

            log_channel = ctx.guild.get_channel(channel_id)
            await log_channel.send(embed=log)

        embed = disnake.Embed(title="", color=disnake.Color.green(),
                              description=f"Заметка {' '.join(notes_number)} для пользователя {user.mention} удалена:\n")
        embed.add_field(name="", value="\n".join(deleted_notes), inline=False)
        embed.add_field(name="", value="❗Воспользуйтесь просмотром журнала, чтобы увидеть обновлённые номера заметок",
                        inline=False)
        await ctx.send(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(Journal(bot))
