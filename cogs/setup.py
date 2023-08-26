import disnake
from disnake.ext import commands
from core.bot import Nexus
import asyncpg


MAX_VIEWS_IN_MENU = 25
MAX_BUTTONS_COUNT = 5


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

    @commands.Cog.listener()
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

    #region Main settings
    async def ask_emojis(self, ctx):
        await ctx.channel.send("Укажите эмодзи лайка и дизлайка через пробел:")
        answer = await self.wait_for_message(ctx)
        answer = answer.content.split()
        emojis = []

        while not emojis:
            try:
                emojis = [emoji for emoji in answer]
            except (ValueError, AttributeError):
                await ctx.channel.send("Произошла ошибка")

        query = "INSERT INTO emoji_reactions (guild_id, _like, _dislike)" \
                "VALUES ($1, $2, 3)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET _like = $2, _dislike = $3"

        await self.pool.execute(query, ctx.guild.id, emojis[0], emojis[1])

    async def ask_art_channel_id(self, ctx):
        await ctx.channel.send("Укажите ID канала для артов\n"
                               "Убедитесь, что у меня есть возможность отправлять там сообщения:")
        art_channel_id = await self.wait_for_message(ctx)
        art_channel = None

        while not art_channel:
            try:
                art_channel_id = int(art_channel_id.content)
                art_channel = self.bot.get_channel(art_channel_id)
            except (ValueError, AttributeError):
                await ctx.channel.send("Канал не найден, попробуйте ещё раз:")
                art_channel_id = await self.wait_for_message(ctx)

        query = "INSERT INTO text_channels (guild_id, art_channel_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET art_channel_id = $2"

        await self.pool.execute(query, ctx.guild.id, art_channel_id)

    async def ask_meme_channel_id(self, ctx):
        await ctx.channel.send("Укажите ID канала для мемов\n"
                               "Убедитесь, что у меня есть возможность отправлять там сообщения:")
        meme_channel_id = await self.wait_for_message(ctx)
        meme_channel = None

        while not meme_channel:
            try:
                meme_channel_id = int(meme_channel_id.content)
                meme_channel = self.bot.get_channel(meme_channel_id)
            except (ValueError, AttributeError):
                await ctx.channel.send("Канал не найден, попробуйте ещё раз:")
                meme_channel_id = await self.wait_for_message(ctx)

        query = "INSERT INTO text_channels (guild_id, meme_channel_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET meme_channel_id = $2"

        await self.pool.execute(query, ctx.guild.id, meme_channel_id)

    async def ask_tickets_category(self, ctx):
        await ctx.channel.send("Укажите ID категории для тикетов:")
        text_channels_category_id = await self.wait_for_message(ctx)
        text_channels_category = None

        while not text_channels_category:
            try:
                text_channels_category_id = int(text_channels_category_id.content)
                text_channels_category = self.bot.get_channel(text_channels_category_id)
            except (ValueError, AttributeError):
                await ctx.channel.send("Категория не найдена, попробуйте ещё раз:")
                text_channels_category_id = await self.wait_for_message(ctx)

        query = "INSERT INTO guild_settings (guild_id, tickets_category_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET tickets_category_id = $2"

        await self.pool.execute(query, ctx.guild.id, text_channels_category_id)

    async def ask_roles_mention_in_tickets(self, ctx):
        await ctx.channel.send("Укажите ID ролей, которые будут иметь доступ к тикетам, через пробел:")
        input_roles = await self.wait_for_message(ctx)
        roles_id = None

        roles = []

        while not roles:
            try:
                roles_id = list(map(int, input_roles.content.split()))
                for role in roles_id:
                    roles.append(ctx.guild.get_role(int(role)))
            except (ValueError, AttributeError):
                await ctx.send("Одна или несколько ролей не были найдены, попробуйте ещё раз:")
                input_roles = await self.wait_for_message(ctx)
                roles_id = input_roles.content.split()

        query = "INSERT INTO text_channels (guild_id, roles_id_to_mention)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET roles_id_to_mention = $2"

        await self.pool.execute(query, ctx.guild.id, roles_id)

    async def ask_button_cooldown(self, ctx):
        await ctx.channel.send("Укажите время (в минутах) между нажатем кнопок для одного пользователя:")
        input_cooldown = await self.wait_for_message(ctx)
        cooldown = None
        while type(cooldown) != int:
            try:
                cooldown = int(input_cooldown.content)
            except (ValueError, AttributeError):
                await ctx.channel.send("Введите только число:")
                input_cooldown = await self.wait_for_message(ctx)
                cooldown = None

        query = "INSERT INTO cooldown (guild_id, button_cooldown)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET button_cooldown = $2"

        await self.pool.execute(query, ctx.guild.id, cooldown)

    async def ask_voice_channels_category(self, ctx):
        await ctx.channel.send("Укажите ID категории для временных голосовых каналов:"
                               "**Перед этим добавьте в категорию следующие разрешения для бота:**\n"
                               "`Просматривать каналы`\n"
                               "`Управлять каналами`\n"
                               "`Управлять правами`\n"
                               "`Перемещать участников`\n"
                               "Введите `skip` для пропуска этапа"
                               )
        category_id = await self.wait_for_message(ctx)
        category = None
        while not category:
            try:
                category_id = int(category_id.content)
                category = self.bot.get_channel(category_id)
                if not isinstance(category, disnake.CategoryChannel):
                    raise ValueError
            except (ValueError, AttributeError):
                await ctx.channel.send("Категория не найдена, попробуйте ещё раз:")
                category_id = await self.wait_for_message(ctx)

        query = "INSERT INTO guild_settings (guild_id, voice_channel_category_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET voice_channel_category_id = $2"

        await self.pool.execute(query, ctx.guild.id, category_id)

        voice_channel = await ctx.guild.create_voice_channel(
            name="【➕】Создать",
            category=category,
            overwrites=category.overwrites
        )

        query = "INSERT INTO guild_settings (guild_id, channel_creator_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET channel_creator_id = $2"

        await self.pool.execute(query, ctx.guild.id, voice_channel.id)
        await ctx.channel.send("В выбранной категории создан голосовой канал\n"
                               "Вы можете изменить его название вручную в любое время")

    #endregion

    # region Setup commands
    @commands.slash_command()
    async def setup(self, ctx):
        pass

    @setup.sub_command()
    async def reactions(self, ctx: disnake.CommandInteraction): ##############
        """Настроить эмодзи"""
        await ctx.send("Начало настройки эмодзи")
        await self.ask_emojis(ctx)
        await ctx.channel.send("Настройка завершена")

    @setup.sub_command()
    async def creative_work(self, ctx: disnake.CommandInteraction):
        """Указать каналы для артов и мемов"""
        print(f"Self: {self}\nCtx: {ctx}")
        await ctx.send("Начало настройки каналов для артов и мемов")
        await self.ask_art_channel_id(ctx)
        await self.ask_meme_channel_id(ctx)
        await ctx.channel.send("Настройка завершена")

    @setup.sub_command()
    async def voice(self, ctx: disnake.CommandInteraction):
        """Указать ID категории для временных каналов"""
        await ctx.send("Начало настройки голосовых каналов")
        await self.ask_voice_channels_category(ctx)
        await ctx.channel.send("Настройка завершена")

    @setup.sub_command()
    async def tickets(self, ctx: disnake.CommandInteraction):
        """Указать категорию для тикетов и роли, которые будут иметь доступ к тикетам"""
        await ctx.send("Начало настройки тикетов")
        await self.ask_tickets_category(ctx)
        await self.ask_roles_mention_in_tickets(ctx)
        await self.ask_button_cooldown(ctx)
        await ctx.channel.send("Настройка завершена")

    @setup.sub_command()
    async def all(self, ctx: disnake.CommandInteraction):
        """Настроить всё сразу"""
        await ctx.send("Начало настройки всего по порядку")
        await self.ask_emojis(ctx)
        await self.ask_art_channel_id(ctx)
        await self.ask_meme_channel_id(ctx)

        await self.ask_tickets_category(ctx)
        await self.ask_roles_mention_in_tickets(ctx)
        await self.ask_button_cooldown(ctx)

        await self.ask_voice_channels_category(ctx)

        await ctx.channel.send("Настройка успешно завершена\nКонец настройки")

    # endregion

    # region Edit commands
    @commands.slash_command()
    async def edit(self, ctx):
        pass

    @edit.sub_command()
    async def emojis(self, ctx: disnake.CommandInteraction, like, dislike):
        """Указать реакции, которые будет оставлять бот под постом

        Parameters
        ----------
        ctx: command interaction
        like: Реакция лайка
        dislike: Реакция дизлайка
        """
        print(f"Like: {like}\nDislike: {dislike}")
        query = "INSERT INTO emoji_reactions (guild_id, _like, _dislike)" \
                "VALUES ($1, $2, 3)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET _like = $2, _dislike = $3"
        await self.pool.execute(query, ctx.guild.id, like, dislike)
        await ctx.send("Настройки сохранены")

    @edit.sub_command()
    async def art_channel(self, ctx: disnake.CommandInteraction, channel: disnake.TextChannel):
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
        await ctx.send("Настройки сохранены")

    @edit.sub_command()
    async def meme_channel(self, ctx: disnake.CommandInteraction, channel: disnake.TextChannel):
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
        await ctx.send("Настройки сохранены")

    @edit.sub_command()
    async def tickets_category(self, ctx: disnake.CommandInteraction, category_id: int):
        """Изменить ID категории для создаваемых тикетов

        Parameters
        ----------
        ctx: command interaction
        category_id: ID категории
        """
        query = "INSERT INTO guild_settings (guild_id, tickets_category_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET tickets_category_id = $2"
        await self.pool.execute(query, ctx.guild.id, category_id)
        await ctx.send("Настройки сохранены")

    @edit.sub_command()
    async def roles_mention(self, ctx: disnake.CommandInteraction, roles):
        """Изменить ID ролей для упоминания при создании тикетов

        Parameters
        ----------
        ctx: command interaction
        roles: Роли для упоминания
        """
        roles_id = [int(role.id) for role in roles]
        query = "INSERT INTO text_channels (guild_id, roles_id_to_mention)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET roles_id_to_mention = $2"
        await self.pool.execute(query, ctx.guild.id, roles_id)
        await ctx.send("Настройки сохранены")

    @edit.sub_command()
    async def button_cooldown(self, ctx: disnake.CommandInteraction, time: int):
        """Изменить кулдаун нажатия на кнопку для каждого пользователя

        Parameters
        ----------
        ctx: command interaction
        time: Количество минут
        """
        query = "INSERT INTO cooldown (guild_id, button_cooldown)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET button_cooldown = $2"

        await self.pool.execute(query, ctx.guild.id, time)
        await ctx.send("Настройки сохранены")

    @edit.sub_command()
    async def voice_channels_category(self, ctx: disnake.CommandInteraction, category_id: int = None,
                                      voice_channel_id: int = None):
        """Изменить ID категории или голосового канала"""
        if category_id:
            query = "INSERT INTO guild_settings (guild_id, voice_channel_category_id)" \
                    "VALUES ($1, $2)" \
                    "ON CONFLICT (guild_id) DO " \
                    "UPDATE SET voice_channel_category_id = $2"
            await self.pool.execute(query, ctx.guild.id, category_id)

        if voice_channel_id:
            query = "INSERT INTO guild_settings (guild_id, channel_creator_id)" \
                    "VALUES ($1, $2)" \
                    "ON CONFLICT (guild_id) DO " \
                    "UPDATE SET channel_creator_id = $2"
            await self.pool.execute(query, ctx.guild.id, voice_channel_id)

        await ctx.send("Настройки сохранены")

    # endregion

    @commands.slash_command()
    async def settings(self, ctx: disnake.ApplicationCommandInteraction, ephemeral: bool = False):
        """Показать настройки сервера"""
        query = ("SELECT * "
                 "FROM text_channels "
                 "WHERE guild_id = $1")
        result = await self.pool.fetch(query, ctx.guild.id)
        art_channel_mention, meme_channel_mention, mention_roles = None, None, []
        if result:
            result = dict(result[0])
            art_channel_id = result.get("art_channel_id")
            meme_channel_id = result.get("meme_channel_id")
            mention_roles_ids = result.get("roles_id_to_mention")

            art_channel_mention = ctx.guild.get_channel(art_channel_id).mention
            meme_channel_mention = ctx.guild.get_channel(meme_channel_id).mention
            mention_roles = [f"{ctx.guild.get_role(role_id).mention}" for role_id in mention_roles_ids]

        query = ("SELECT * "
                 "FROM emoji_reactions "
                 "WHERE guild_id = $1")
        result = await self.pool.fetch(query, ctx.guild.id)
        like, dislike = None, None
        if result:
            result = dict(result[0])
            like = result.get("_like")
            dislike = result.get("_dislike")

        query = ("SELECT * "
                 "FROM guild_settings "
                 "WHERE guild_id = $1")
        result = await self.pool.fetch(query, ctx.guild.id)
        tickets_category, voice_category, channel_creator_mention = None, None, None
        if result:
            result = dict(result[0])
            tickets_category_id = result.get("tickets_category_id")
            voice_category_id = result.get("voice_channel_category_id")
            channel_creator_id = result.get("channel_creator_id")

            tickets_category = ctx.guild.get_channel(tickets_category_id)
            voice_category = ctx.guild.get_channel(voice_category_id)
            channel_creator_mention = ctx.guild.get_channel(channel_creator_id).mention

        query = ("SELECT button_cooldown "
                 "FROM cooldown "
                 "WHERE guild_id = $1")
        result = await self.pool.fetch(query, ctx.guild.id)
        button_cooldown = None
        if result:
            result = dict(result[0])
            button_cooldown = result.get("button_cooldown")

        embed = (
            disnake.Embed(
                title="Настройки сервера",
                color=disnake.Color.blurple()
            )
            .add_field("Канал для артов", art_channel_mention, inline=True)
            .add_field("Канал для мемов", meme_channel_mention, inline=True)
            .add_field("Реакции под постами", f"\n{like} {dislike}", inline=True)
            .add_field("Категория тикетов", tickets_category, inline=True)
            .add_field("Роли для упоминания", '\n'.join(mention_roles) if mention_roles else None, inline=True)
            .add_field("Кулдаун кнопок (в минутах)", button_cooldown, inline=True)
            .add_field("Категория голосовых каналов", voice_category, inline=True)
            .add_field("Генератор голосовых каналов", channel_creator_mention, inline=True)
            .add_field("", "", inline=True)
        )

        await ctx.send(embed=embed, ephemeral=ephemeral)


def setup(bot):
    bot.add_cog(SetupBot(bot))
