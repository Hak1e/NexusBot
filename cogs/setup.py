import disnake
from disnake.ext import commands
from core.bot import Nexus
import asyncpg
import re

MAX_VIEWS_IN_MENU = 25
MAX_BUTTONS_COUNT = 5


# TODO: сделать команду для создания рейтинговой комнаты со всеми нужными аргументами сразу


class SelectRoles(disnake.ui.Select):
    def __init__(self, roles, row):
        options = [disnake.SelectOption(label="Не выбрано", value="none")]
        for role in roles:
            options.append(disnake.SelectOption(label=role.name, value=str(role.id)))

        super().__init__(
            placeholder=f"{row} часть. Выберите роли",
            min_values=1,
            max_values=len(roles),
            options=options
        )
        self.selected_roles_id = []

    async def callback(self, ctx: disnake.MessageInteraction):
        if not ctx.values:
            await ctx.response.defer()
        else:
            self.selected_roles_id = [role_id for role_id in ctx.values]
            if "none" in self.selected_roles_id:
                self.selected_roles_id.remove("none")
            await ctx.response.defer()


class SelectSettings(disnake.ui.Select):
    def __init__(self, options):

        super().__init__(
            placeholder=f"Выберите настройки",
            min_values=1,
            max_values=25,
            options=options
        )

    async def callback(self, ctx: disnake.MessageInteraction):
        if not ctx.values:
            await ctx.response.defer()
        else:
            await ctx.response.defer()


class SetupBot(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.get_pool()

        self.view_list = []
        self.sent_messages = []

    # @commands.slash_command()
    async def select_roles(self, ctx: disnake.CommandInteraction, roles_reverse: bool = True):
        """Настройки временного канала. Выбор ролей для доступа ко временному текстовому каналу
        Parameters
        ----------
        ctx: command ctx
        roles_reverse: Сортировка ролей. По стандарту (True) роли сверху вниз
        """
        await ctx.send("Выберите роли, которые будут получать уведомление при создании тикета:")
        await ctx.delete_original_message(delay=10)

        roles = ctx.guild.roles
        if roles_reverse:
            roles.reverse()

        role_chunks = [roles[i:i + MAX_VIEWS_IN_MENU - 1] for i in range(1, len(roles), MAX_VIEWS_IN_MENU)]
        view = disnake.ui.View(timeout=None)

        loop_run_times = 1
        if len(role_chunks) > 5:
            loop_run_times = len(role_chunks) // MAX_BUTTONS_COUNT + 1

        row = 1
        chunk_position = 0
        while loop_run_times > 0:
            while chunk_position <= len(role_chunks):
                current_number_of_buttons = len(view.children)

                if chunk_position == len(role_chunks):
                    self.sent_messages.append(await ctx.channel.send(view=view))
                    self.view_list.append(view)
                    loop_run_times -= 1

                elif current_number_of_buttons < MAX_BUTTONS_COUNT:
                    view.add_item(SelectRoles(role_chunks[chunk_position], row))
                    row += 1

                else:
                    self.sent_messages.append(await ctx.channel.send(view=view))
                    self.view_list.append(view)
                    loop_run_times -= 1
                    view = disnake.ui.View(timeout=None)
                    break

                chunk_position += 1

        self.sent_messages.append(
            await ctx.channel.send(
                "Нажмите кнопку ниже для продолжения",
                components=[
                    disnake.ui.Button(
                        label="Next",
                        style=disnake.ButtonStyle.primary,
                        custom_id="next_button"
                    )
                ]
            )
        )

    # @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if ctx.component.custom_id == "next_button":
            all_selected_roles_id = []

            for view in self.view_list:
                for child in view.children:
                    if isinstance(child, SelectRoles):
                        all_selected_roles_id.extend([int(role_id) for role_id in child.selected_roles_id])

            query = "UPDATE text_channels " \
                    "SET roles_id_to_mention = roles_id_to_mention || $2 " \
                    "WHERE guild_id = $1"
            await self.pool.execute(query, ctx.guild.id,
                                    all_selected_roles_id)

            for message in self.sent_messages:
                await message.delete()

            await ctx.send("Настройка завершена\nКонец настройки", ephemeral=True)

    async def wait_for_message(self, ctx):
        def check(msg):
            return msg.author.id == ctx.author.id and msg.channel == ctx.channel

        return await self.bot.wait_for("message", check=check)

    @commands.slash_command()
    async def set(self, ctx):
        pass

    @set.sub_command()
    async def error_logs_channel(self, ctx: disnake.CmdInter,
                                 channel: disnake.TextChannel):
        """Указать канал, в который будет отправляться ошибка. Доступно только создателю

        Parameters
        ----------

        ctx: command interaction
        channel: ID канала
        """
        channel_id = channel.id or int(channel)  # type: ignore
        query = ("INSERT INTO error_logs_channel (guild_id, channel_id) "
                 "VALUES ($1, $2) "
                 "ON CONFLICT (guild_id) DO "
                 "UPDATE SET channel_id = $2")
        await self.pool.execute(query, ctx.guild.id, channel_id)
        await ctx.send("Настройки сохранены", ephemeral=True)

    @set.sub_command()
    async def user_left_log(self, ctx: disnake.CommandInteraction,
                            channel: disnake.TextChannel):
        """Указать канал, в котором будет лог вышедших пользователей

        Parameters
        ----------
        ctx: command interaction
        channel: Текстовый канал
        """
        query = "INSERT INTO text_channels (guild_id, goodbye_channel_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET goodbye_channel_id = $2"
        await self.pool.execute(query, ctx.guild.id, channel.id)
        await ctx.send("Настройки сохранены", ephemeral=True)

    @set.sub_command()
    async def journal_logs(self, ctx: disnake.CmdInter,
                           channel: disnake.TextChannel):
        channel_id = channel.id or int(channel)  # type: ignore
        query = "INSERT INTO journal_logs (guild_id, channel_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET channel_id = $2"

        await self.pool.execute(query, ctx.guild.id, channel_id)

    # region Tickets
    @commands.slash_command()
    async def tickets(self, ctx: disnake.CmdInter):
        """Настройка тикетов"""
        pass

    @tickets.sub_command()
    async def cooldown(self, ctx: disnake.CmdInter,
                       button_cooldown):
        """Настройка кулдауна кнопок тикетов

        Parameters
        ----------
        ctx: command interaction
        button_cooldown: Настройка кулдауна нажатия на кнопку
        """
        query = "INSERT INTO tickets (guild_id, button_cooldown)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET button_cooldown = $2"
        await self.pool.execute(query, ctx.guild.id, int(button_cooldown))
        await ctx.send("Настройки сохранены", ephemeral=True)

    @tickets.sub_command()
    async def categories(self, ctx: disnake.CmdInter,
                         tickets_category: disnake.CategoryChannel = None,
                         closed_tickets_category: disnake.CategoryChannel = None):
        """Настройка категорий тикетов

        Parameters
        ----------
        ctx: command interaction
        tickets_category: Указать категорию тикетов
        closed_tickets_category: Указать категорию закрытых тикетов
        """
        tickets_category_id = tickets_category.id or int(tickets_category)  # type: ignore
        closed_tickets_category_id = closed_tickets_category.id or int(closed_tickets_category)  # type: ignore
        if tickets_category_id:
            query = "INSERT INTO tickets (guild_id, tickets_category_id)" \
                    "VALUES ($1, $2)" \
                    "ON CONFLICT (guild_id) DO " \
                    "UPDATE SET tickets_category_id = $2"
            await self.pool.execute(query, ctx.guild.id, int(tickets_category_id))
        if closed_tickets_category_id:
            query = "INSERT INTO tickets (guild_id, closed_tickets_category_id)" \
                    "VALUES ($1, $2)" \
                    "ON CONFLICT (guild_id) DO " \
                    "UPDATE SET closed_tickets_category_id = $2"
            await self.pool.execute(query, ctx.guild.id, int(closed_tickets_category_id))
        await ctx.send("Настройки сохранены", ephemeral=True)

    @staticmethod
    async def get_roles_id(roles_str) -> list:
        roles_ids = []
        for string in roles_str:
            split_ids = re.split("<@&|>", string)
            for item in split_ids:
                if item:
                    roles_ids.append(int(item))

        return roles_ids

    @tickets.sub_command()
    async def roles(self, ctx: disnake.CmdInter,
                    question_roles_ids=None, report_roles_ids=None,
                    offer_roles_ids=None):
        """Настройка ролей, имеющих доступ к тикетам

        Parameters
        ----------
        ctx: command interaction
        question_roles_ids: Указать роли или их ID для вопроса. Перечислить через пробел
        report_roles_ids: Указать роли или их ID для жалобы. Перечислить через пробел
        offer_roles_ids: Указать роли или их ID для предложения. Перечислить через пробел
        """
        if question_roles_ids:
            query = "INSERT INTO tickets (guild_id, question_roles_ids)" \
                    "VALUES ($1, $2)" \
                    "ON CONFLICT (guild_id) DO " \
                    "UPDATE SET question_roles_ids = $2"
            await self.pool.execute(query, ctx.guild.id,
                                    await self.get_roles_id(question_roles_ids.split()))

        if report_roles_ids:
            query = "INSERT INTO tickets (guild_id, report_roles_ids)" \
                    "VALUES ($1, $2)" \
                    "ON CONFLICT (guild_id) DO " \
                    "UPDATE SET report_roles_ids = $2"
            await self.pool.execute(query, ctx.guild.id,
                                    await self.get_roles_id(report_roles_ids.split()))

        if offer_roles_ids:
            query = "INSERT INTO tickets (guild_id, offer_roles_ids)" \
                    "VALUES ($1, $2)" \
                    "ON CONFLICT (guild_id) DO " \
                    "UPDATE SET offer_roles_ids = $2"
            await self.pool.execute(query, ctx.guild.id,
                                    await self.get_roles_id(offer_roles_ids.split()))

        await ctx.send("Настройки сохранены", ephemeral=True)

    @tickets.sub_command()
    async def show_roles(self, ctx: disnake.CmdInter,
                         ephemeral: bool = True):
        """Показать роли, которые имеют доступ к тикетам"""
        question_roles_id_query = ("SELECT question_roles_ids "
                                   "FROM tickets "
                                   "WHERE guild_id = $1")
        question_roles_ids = await self.pool.fetch(question_roles_id_query, ctx.guild.id)
        question_roles = []
        if question_roles_ids:
            for record in question_roles_ids:
                for role_id in record["question_roles_ids"]:
                    question_roles.append(ctx.guild.get_role(int(role_id)).mention)

        report_roles_id_query = ("SELECT report_roles_ids "
                                 "FROM tickets "
                                 "WHERE guild_id = $1")
        report_roles_ids = await self.pool.fetch(report_roles_id_query, ctx.guild.id)
        report_roles = []
        if report_roles_ids:
            for record in report_roles_ids:
                for role_id in record["report_roles_ids"]:
                    report_roles.append(ctx.guild.get_role(int(role_id)).mention)

        offer_roles_id_query = ("SELECT offer_roles_ids "
                                "FROM tickets "
                                "WHERE guild_id = $1")
        offer_roles_ids = await self.pool.fetch(offer_roles_id_query, ctx.guild.id)
        offer_roles = []
        if offer_roles_ids:
            for record in offer_roles_ids:
                for role_id in record["offer_roles_ids"]:
                    offer_roles.append(ctx.guild.get_role(int(role_id)).mention)
        roles_not_found_message = "Нет"
        embed = (
            disnake.Embed(title="Роли с доступом к тикетам")
            .add_field(name="Вопрос",
                       value=f"{"\n".join(question_roles) if question_roles else roles_not_found_message}")
            .add_field(name="Жалоба", value=f"{"\n".join(report_roles) if report_roles else roles_not_found_message}")
            .add_field(name="Предложение",
                       value=f"{"\n".join(offer_roles) if offer_roles else roles_not_found_message}")
        )
        await ctx.send(embed=embed, ephemeral=ephemeral)

    @tickets.sub_command()
    async def buttons_emoji(self, ctx: disnake.CmdInter,
                            question_button=None, report_button=None,
                            offer_button=None, close_button=None,
                            delete_button=None):
        """Поменять эмодзи кнопок

        Parameters
        ----------

        ctx: command interaction
        question_button: Кнопка "Вопрос"
        report_button: Кнопка "Жалоба"
        offer_button: Кнопка "Предложение"
        close_button: Кнопка "Закрыть тикет"
        delete_button: Кнопка "Удалить тикет"
        """
        if question_button:
            query = ("INSERT INTO ticket_buttons_emojis (guild_id, question_button_emoji) "
                     "VALUES ($1, $2) "
                     "ON CONFLICT (guild_id) DO "
                     "UPDATE SET question_button_emoji = $2")
            await self.pool.execute(query, ctx.guild.id, question_button)
        if report_button:
            query = ("INSERT INTO ticket_buttons_emojis (guild_id, report_button_emoji) "
                     "VALUES ($1, $2) "
                     "ON CONFLICT (guild_id) DO "
                     "UPDATE SET report_button_emoji = $2")
            await self.pool.execute(query, ctx.guild.id, report_button)
        if offer_button:
            query = ("INSERT INTO ticket_buttons_emojis (guild_id, offer_button_emoji) "
                     "VALUES ($1, $2) "
                     "ON CONFLICT (guild_id) DO "
                     "UPDATE SET offer_button_emoji = $2")
            await self.pool.execute(query, ctx.guild.id, offer_button)
        if close_button:
            query = ("INSERT INTO ticket_buttons_emojis (guild_id, close_button_emoji) "
                     "VALUES ($1, $2) "
                     "ON CONFLICT (guild_id) DO "
                     "UPDATE SET close_button_emoji = $2")
            await self.pool.execute(query, ctx.guild.id, close_button)
        if delete_button:
            query = ("INSERT INTO ticket_buttons_emojis (guild_id, delete_button_emoji) "
                     "VALUES ($1, $2) "
                     "ON CONFLICT (guild_id) DO "
                     "UPDATE SET delete_button_emoji = $2")
            await self.pool.execute(query, ctx.guild.id, delete_button)
        await ctx.send("Настройки сохранены", ephemeral=True)

    @tickets.sub_command()
    async def logs(self, ctx: disnake.CmdInter,
                   channel: disnake.TextChannel):
        """Указать канал для логов тикетов"""
        channel_id = channel.id or int(channel)  # type: ignore
        query = ("INSERT INTO tickets(guild_id, logs_channel_id) "
                 "VALUES ($1, $2)"
                 "ON CONFLICT (guild_id) DO "
                 "UPDATE SET logs_channel_id = $2")
        await self.pool.execute(query, ctx.guild.id, channel_id)
        await ctx.send("Настройки сохранены", ephemeral=True)

    @tickets.sub_command()
    async def tickets_category(self, ctx: disnake.CommandInteraction,
                               category: disnake.CategoryChannel):
        """Изменить ID категории для создаваемых тикетов"""
        category_id = category.id or int(category)  # type: ignore
        query = "INSERT INTO guild_settings (guild_id, tickets_category_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET tickets_category_id = $2"
        await self.pool.execute(query, ctx.guild.id, category_id)
        await ctx.send("Настройки сохранены", ephemeral=True)

    @tickets.sub_command()
    async def roles_mention(self, ctx: disnake.CommandInteraction,
                            roles_ids):
        """Изменить ID ролей для упоминания при создании тикетов

        Parameters
        ----------
        ctx: command interaction
        roles_ids: ID ролей для упоминания
        """
        roles_id = [int(role) for role in roles_ids.split()]

        query = "INSERT INTO text_channels (guild_id, roles_id_to_mention)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET roles_id_to_mention = $2"
        await self.pool.execute(query, ctx.guild.id, roles_id)
        await ctx.send("Настройки сохранены", ephemeral=True)

    # endregion

    # region Creativity
    @set.sub_command_group()
    async def creativity(self, ctx):
        """Настройка канала для артов, мемов, реакций под постами"""
        pass

    @creativity.sub_command()
    async def emojis(self, ctx: disnake.CommandInteraction,
                     like, dislike):
        """Указать реакции, которые будет оставлять бот под постом

        Parameters
        ----------
        ctx: command interaction
        like: Реакция лайка
        dislike: Реакция дизлайка
        """
        query = "INSERT INTO emoji_reactions (guild_id, _like, _dislike)" \
                "VALUES ($1, $2, $3)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET _like = $2, _dislike = $3"
        await self.pool.execute(query, ctx.guild.id, like, dislike)
        await ctx.send("Настройки сохранены", ephemeral=True)

    @creativity.sub_command()
    async def art_channel(self, ctx: disnake.CommandInteraction,
                          channel: disnake.TextChannel):
        """Изменить ID канала для артов

        Parameters
        ----------
        ctx: command interaction
        channel: Канал для артов
        """
        query = "INSERT INTO text_channels (guild_id, art_channel_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET art_channel_id = $2"
        await self.pool.execute(query, ctx.guild.id, channel.id)
        await ctx.send("Настройки сохранены", ephemeral=True)

    @creativity.sub_command()
    async def meme_channel(self, ctx: disnake.CommandInteraction,
                           channel: disnake.TextChannel):
        """Изменить ID канала для мемов

        Parameters
        ----------
        ctx: command interaction
        channel: Канал для мемов
        """
        query = "INSERT INTO text_channels (guild_id, meme_channel_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET meme_channel_id = $2"
        await self.pool.execute(query, ctx.guild.id, channel.id)
        await ctx.send("Настройки сохранены", ephemeral=True)

    # endregion

    # region Lobby
    @commands.slash_command()
    async def lobby(self, ctx):
        """Настроить создание лобби-каналов"""
        pass

    @lobby.sub_command()
    async def creators(self, ctx: disnake.CmdInter,
                       channels_creators_ids, category: disnake.CategoryChannel,
                       user_limit):
        """Указать категорию, в которой будет создан канал при заходе в канал-генератор

        Parameters
        ----------

        ctx: command interaction
        channels_creators_ids: ID каналов, в которые нужно зайти для создания лобби
        category: Категория, в которой будет создан новый канал
        user_limit: Лимит пользователей для каждого канала через пробел

        """
        if isinstance(channels_creators_ids, disnake.VoiceChannel):
            return await ctx.send("Укажите ID каналов, а не их упоминание", ephemeral=True)
        category_id = category.id or int(category)  # type: ignore
        channels_creators_ids = re.split(", |,| ,| ", channels_creators_ids)
        channels_creators_ids = map(int, channels_creators_ids)
        user_limit = re.split(", |,| ,| ", user_limit)
        user_limit = map(int, user_limit)
        for channel_creator_id, limit in zip(channels_creators_ids, user_limit):
            query = ("INSERT INTO lobby_voice_channel_creator_settings(id, category_id_for_new_channel, user_limit) "
                     "VALUES ($1, $2, $3) "
                     "ON CONFLICT (id) DO "
                     "UPDATE SET category_id_for_new_channel = $2, user_limit = $3")
            await self.pool.execute(query, channel_creator_id,
                                    category_id, limit)
        await ctx.send("Настройки сохранены", ephemeral=True)

    @lobby.sub_command()
    async def info(self, ctx: disnake.CmdInter,
                   channels_creators_ids, text_channel: disnake.TextChannel):
        """Указать канал, в который будут отправляться сообщения о созданных лобби

        Parameters
        ----------

        ctx: command interaction
        text_channel: Текстовый канал, куда будут отправляться сообщения о лобби
        channels_creators_ids: Голосовые каналы, в которые нужно зайти для создания лобби
        """
        if isinstance(channels_creators_ids, disnake.VoiceChannel):
            return await ctx.send("Укажите ID каналов, а не их упоминание", ephemeral=True)
        text_channel_id = text_channel.id or int(text_channel)  # type: ignore
        channels_creators_ids = re.split(", |,| ,| ", channels_creators_ids)
        channels_creators_ids = map(int, channels_creators_ids)
        for channel_creator_id in channels_creators_ids:
            query = ("INSERT INTO lobby_text_channel (id, voice_channel_creator_id, guild_id) "
                     "VALUES ($1, $2, $3) "
                     "ON CONFLICT (id, voice_channel_creator_id) DO UPDATE "
                     "SET id = $3")
            await self.pool.execute(query, text_channel_id,
                                    channel_creator_id, ctx.guild.id)
        await ctx.send("Настройки сохранены", ephemeral=True)

    @lobby.sub_command()
    async def default_name(self, ctx: disnake.CmdInter,
                           channels_creators_ids, name):
        """Установить название канала, если нет роли

        Parameters
        ----------

        ctx: command interaction
        channels_creators_ids: ID каналов-создателей
        name: Название для созданного канала
        """
        if isinstance(channels_creators_ids, disnake.VoiceChannel):
            return await ctx.send("Укажите ID каналов, а не их упоминание", ephemeral=True)
        channels_creators_ids = re.split(", |,| ,| ", channels_creators_ids)
        channels_creators_ids = map(int, channels_creators_ids)
        for channel_creator_id in channels_creators_ids:
            query = ("INSERT INTO lobby_voice_channel_creator_settings (id, default_name) "
                     "VALUES ($1, $2) "
                     "ON CONFLICT (id) DO "
                     "UPDATE SET default_name = $3")
            await self.pool.execute(query, channel_creator_id,
                                    name)

        await ctx.send("Настройки сохранены", ephemeral=True)

    @lobby.sub_command()
    async def role_not_found_message(self, ctx: disnake.CmdInter,
                                     channels_creators_ids, message):
        """Сообщение, которое отправит бот, если не была найдена нужная роль

        Parameters
        ----------

        ctx: command interaction
        channels_creators_ids: ID каналов-создателей
        message: Сообщение, которое будет отправлено в канал, если у участника нет нужной роли
        """
        if isinstance(channels_creators_ids, disnake.VoiceChannel):
            return await ctx.send("Укажите ID каналов, а не их упоминание", ephemeral=True)
        channels_creators_ids = re.split(", |,| ,| ", channels_creators_ids)
        channels_creators_ids = map(int, channels_creators_ids)
        for channel_creator_id in channels_creators_ids:
            query = ("INSERT INTO lobby_voice_channel_creator_settings (id, role_not_found_message) "
                     "VALUES ($1, $2) "
                     "ON CONFLICT (id) DO "
                     "UPDATE SET role_not_found_message = $3")
            await self.pool.execute(query, channel_creator_id,
                                    message)
        await ctx.send("Настройки сохранены", ephemeral=True)

    @lobby.sub_command()
    async def add_roles_for_channels_creators(self, ctx: disnake.CmdInter,
                                              channels_creators_ids, roles_ids=None):
        """Добавить роль, с которой можно зайти в канал

        Parameters
        ----------

        ctx: command interaction
        channels_creators_ids: ID каналов-создателей
        roles_ids: ID ролей, которые нужно добавить
        """
        if isinstance(channels_creators_ids, disnake.VoiceChannel):
            return await ctx.send("Укажите ID каналов, а не их упоминание", ephemeral=True)
        channels_creators_ids = re.split(", |,| ,| ", channels_creators_ids)
        channels_creators_ids = map(int, channels_creators_ids)
        if roles_ids:
            if isinstance(roles_ids, disnake.Role):
                return await ctx.send("Укажите ID роли или ролей", ephemeral=True)
            for channel_creator_id in channels_creators_ids:
                for role_id in roles_ids:
                    query = ("INSERT INTO lobby_voice_channel_creator_role (voice_channel_id, role_id, guild_id) "
                             "VALUES ($1, $2, $3)")
                    await self.pool.execute(query, ctx.guild.id,
                                            channel_creator_id, role_id)
                    query = ("UPDATE lobby_voice_channel_creator_settings "
                             "SET role_needed = $2 "
                             "WHERE id = $1")
                    await self.pool.execute(query, channel_creator_id,
                                            True)
        await ctx.send("Настройки сохранены", ephemeral=True)

    @lobby.sub_command()
    async def remove_roles_for_category(self, ctx: disnake.CmdInter,
                                        channels_creators_ids, roles_ids=None,
                                        role_needed: bool = None):
        """Удалить роль, с которой можно зайти в канал

        Parameters
        ----------

        ctx: command interaction
        channels_creators_ids: ID каналов-создателей
        roles_ids: ID ролей
        role_needed: Требуется ли наличие роли для этой категории. Укажите False, если нет
        """
        if isinstance(channels_creators_ids, disnake.VoiceChannel):
            return await ctx.send("Укажите ID каналов, а не их упоминание", ephemeral=True)
        channels_creators_ids = re.split(", |,| ,| ", channels_creators_ids)
        channels_creators_ids = map(int, channels_creators_ids)
        if roles_ids:
            for channel_creator_id in channels_creators_ids:
                for role_id in roles_ids:
                    query = ("DELETE FROM lobby_voice_channel_creator_role "
                             "WHERE voice_channel_id = $1 and role_id = $2 and guild_id = $3")
                    await self.pool.execute(query, channel_creator_id,
                                            role_id, ctx.guild.id)
        if role_needed:
            for channel_creator_id in channels_creators_ids:
                query = ("UPDATE lobby_voice_channel_creator_settings "
                         "SET role_needed = $2 "
                         "WHERE id = $1")
                await self.pool.execute(query, channel_creator_id,
                                        role_needed)
        await ctx.send("Настройки сохранены", ephemeral=True)

    @lobby.sub_command()
    async def list_roles(self, ctx: disnake.CmdInter,
                         channel: disnake.VoiceChannel, ephemeral: bool = True):
        """Получить список всех ролей с доступом к комнатам рейтинга

        Parameters
        ----------

        ctx: command interaction
        channel: Канал-создатель
        ephemeral: Будет ли сообщение видно всем или только Вам
        """
        channel_id = channel.id or int(channel)  # type: ignore
        role_needed_query = ("SELECT role_needed "
                             "FROM lobby_voice_channel_creator_settings "
                             "WHERE id = $1")
        is_role_needed = await self.pool.fetchval(role_needed_query, channel_id)
        if not is_role_needed:
            embed = disnake.Embed(title=f"Роли канала {ctx.guild.get_channel(channel_id)}", color=disnake.Color.blurple())
            embed.add_field(name="", value="Наличие роли не требуется")
            return await ctx.send(embed=embed, ephemeral=ephemeral)

        query = ("SELECT role_id "
                 "FROM lobby_voice_channel_creator_role "
                 "WHERE voice_channel_id = $1 and guild_id = $2")
        result = await self.pool.fetch(query, channel_id,
                                       ctx.guild.id)
        roles_ids = []
        if not result:
            embed = disnake.Embed(title=f"Роли канала {ctx.guild.get_channel(channel_id)}", color=disnake.Color.red())
            embed.add_field(name="", value="Роли не найдены")
            return await ctx.send(embed=embed, ephemeral=ephemeral)

        counter = 1
        for record in result:
            roles_ids.append(f"{counter}) <@&{record["role_id"]}>")
            counter += 1
        embed = (
            disnake.Embed(title=f"Роли категории {ctx.guild.get_channel(channel_id).name}")
            .add_field(name="", value="\n".join(roles_ids))
        )

        await ctx.send(embed=embed, ephemeral=ephemeral)

    # endregion

    # @set.sub_command()
    # async def voice_channels_category(self, ctx: disnake.CommandInteraction, category_id=None,
    #                                   voice_channel_id=None):
    #     """Изменить ID категории или голосового канала"""
    #     if category_id:
    #         query = "INSERT INTO guild_settings (guild_id, voice_channel_category_id)" \
    #                 "VALUES ($1, $2)" \
    #                 "ON CONFLICT (guild_id) DO " \
    #                 "UPDATE SET voice_channel_category_id = $2"
    #         await self.pool.execute(query, ctx.guild.id, int(category_id))
    #
    #     if voice_channel_id:
    #         query = "INSERT INTO guild_settings (guild_id, channel_creator_id)" \
    #                 "VALUES ($1, $2)" \
    #                 "ON CONFLICT (guild_id) DO " \
    #                 "UPDATE SET channel_creator_id = $2"
    #         await self.pool.execute(query, ctx.guild.id, int(voice_channel_id))
    #
    #     await ctx.send("Настройки сохранены", ephemeral=True)

    # @set.sub_command()
    # async def create_voice_generator(self, ctx: disnake.CommandInteraction,
    #                                  user_limit: int, category_id,
    #                                  channel: t.Optional[disnake.VoiceChannel] = None):
    #     """Создать генератор комнат
    #
    #     Parameters
    #     ----------
    #     ctx: command interaction
    #     user_limit: Лимит участников комнаты
    #     category_id: ID категории
    #     channel: Существующий канал или его ID
    #     """
    #     category = ctx.guild.get_channel(category_id)
    #     voice_channel = None
    #     if not channel:
    #         voice_channel = await ctx.guild.create_voice_channel(
    #             name="【➕】Создать",
    #             category=category,
    #             overwrites=category.overwrites
    #         )
    #     channel_id = channel.id or voice_channel
    #     query = ("INSERT INTO voice_creators "
    #              "VALUES ($1, $2, $3, $4)")
    #     await self.pool.execute(query, ctx.guild.id,
    #                             category.id, channel_id,
    #                             user_limit)

    # disabled
    # async def settings(self, ctx: disnake.ApplicationCommandInteraction, ephemeral: bool = False):
    #     """Показать настройки сервера"""
    #     query = ("SELECT * "
    #              "FROM text_channels "
    #              "WHERE guild_id = $1")
    #     result = await self.pool.fetchrow(query, ctx.guild.id)
    #     art_channel_mention, meme_channel_mention, mention_roles = None, None, []
    #     if result:
    #         result = dict(result)
    #         art_channel_id = result.get("art_channel_id")
    #         if art_channel_id:
    #             art_channel_mention = ctx.guild.get_channel(int(art_channel_id)).mention
    #
    #         meme_channel_id = result.get("meme_channel_id")
    #         if meme_channel_id:
    #             meme_channel_mention = ctx.guild.get_channel(int(meme_channel_id)).mention
    #
    #         mention_roles_ids = result.get("roles_id_to_mention")
    #         if mention_roles_ids:
    #             mention_roles = [f"{ctx.guild.get_role(int(role_id)).mention}" for role_id in mention_roles_ids]
    #
    #     query = ("SELECT * "
    #              "FROM emoji_reactions "
    #              "WHERE guild_id = $1")
    #     result = await self.pool.fetchrow(query, ctx.guild.id)
    #     like, dislike = None, None
    #     if result:
    #         result = dict(result)
    #         like = result.get("_like")
    #         dislike = result.get("_dislike")
    #
    #     query = ("SELECT * "
    #              "FROM guild_settings "
    #              "WHERE guild_id = $1")
    #     result = await self.pool.fetchrow(query, ctx.guild.id)
    #     tickets_category, voice_category, channel_creator_mention = None, None, None
    #     if result:
    #         result = dict(result)
    #         tickets_category_id = result.get("tickets_category_id")
    #         if tickets_category_id:
    #             tickets_category = ctx.guild.get_channel(int(tickets_category_id))
    #
    #         voice_category_id = result.get("voice_channel_category_id")
    #         if voice_category_id:
    #             voice_category = ctx.guild.get_channel(int(voice_category_id))
    #
    #         channel_creator_id = result.get("channel_creator_id")
    #         if channel_creator_id:
    #             channel_creator_mention = ctx.guild.get_channel(int(channel_creator_id)).mention
    #
    #     query = ("SELECT button_cooldown "
    #              "FROM cooldown "
    #              "WHERE guild_id = $1")
    #     result = await self.pool.fetchval(query, ctx.guild.id)
    #     button_cooldown = result or None
    #
    #     query = ("SELECT channel_id "
    #              "FROM journal_logs "
    #              "WHERE guild_id = $1")
    #     result = await self.pool.fetchval(query, ctx.guild.id)
    #     journal_channel_mention = None
    #     if result:
    #         journal_channel_mention = ctx.guild.get_channel(result).mention
    #
    #     query = ("SELECT role_id "
    #              "FROM muted_role "
    #              "WHERE guild_id = $1")
    #     result = await self.pool.fetchval(query, ctx.guild.id)
    #     muted_role_mention = None
    #     if result:
    #         muted_role_mention = ctx.guild.get_role(result).mention
    #
    #     embed = (
    #         disnake.Embed(
    #             title="Настройки сервера",
    #             color=disnake.Color.blurple()
    #         )
    #         .add_field("Канал для артов", art_channel_mention, inline=True)
    #         .add_field("Канал для мемов", meme_channel_mention, inline=True)
    #         .add_field("Реакции под постами", f"\n{like} {dislike}", inline=True)
    #         .add_field("Категория тикетов", tickets_category, inline=True)
    #         .add_field("Роли для упоминания", '\n'.join(mention_roles) if mention_roles else None, inline=True)
    #         .add_field("Кулдаун кнопок (в минутах)", button_cooldown, inline=True)
    #         .add_field("Категория голосовых каналов", voice_category, inline=True)
    #         .add_field("Генератор голосовых каналов", channel_creator_mention, inline=True)
    #         .add_field("", "", inline=True)
    #         .add_field("Канал для логов журнала", journal_channel_mention, inline=True)
    #         .add_field("Роль мьюта", muted_role_mention, inline=True)
    #     )
    #
    #     await ctx.send(embed=embed, ephemeral=ephemeral)


def setup(bot):
    bot.add_cog(SetupBot(bot))
