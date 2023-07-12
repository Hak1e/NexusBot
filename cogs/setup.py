import disnake
from disnake.ext import commands
from disnake import SelectOption
import os
from dotenv import load_dotenv
from core.bot import Nexus
from cogs.temp_voice_channel import OnJoinChannel
import asyncpg

load_dotenv()

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

    async def callback(self, interaction: disnake.MessageInteraction):
        if not interaction.values:
            await interaction.response.defer()
        else:
            self.selected_roles_id = [role_id for role_id in interaction.values]
            if "none" in self.selected_roles_id:
                self.selected_roles_id.remove("none")
            await interaction.response.defer()


# На будущее
class TextChannel(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.get_pool()
        self.view_list = []
        self.sent_messages = []

    @commands.slash_command()
    async def select_roles(
            self,
            ctx: disnake.CommandInteraction,
            roles_reverse: bool = True
    ):
        """Настройки временного канала. Выбор ролей для доступа ко временному текстовому каналу
        Parameters
        ----------
        ctx: command ctx
        roles_reverse: сортировка ролей. По стандарту (True) роли сверху вниз
        """
        await ctx.send("Выберите роли, которые будут получать уведомление при создании тикета:")
        await ctx.delete_original_message(delay=10)

        roles = ctx.guild.roles
        if roles_reverse:
            roles.reverse()

        role_chunks = [roles[i:i + MAX_VIEWS_IN_MENU - 1] for i in range(1, len(roles), MAX_VIEWS_IN_MENU)]
        view = disnake.ui.View(timeout=None)

        loop_run_times = 1  # если чанков < 5, цикл отработает всего 1 раз
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

            query = "UPDATE guild_settings " \
                    "SET roles_id_to_mention = roles_id_to_mention || $2 " \
                    "WHERE guild_id = $1"
            await self.pool.execute(
                query,
                ctx.guild.id,
                all_selected_roles_id
            )

            for message in self.sent_messages:
                await message.delete()

            await ctx.send("Настройки сохранены", ephemeral=True)



# TODO: добавить команду, которая позволяет модераторам добавить в тикет людей

class SetupBot(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.get_pool()

    async def save_settings(self, query, *args):
        async with self.pool.acquire() as conn:
            await conn.execute(query, *args)

    async def wait_for_message(self, ctx):
        def check(msg):
            return msg.author.id == ctx.author.id and msg.channel == ctx.channel

        return await self.bot.wait_for("message", check=check)

    async def ask_voice_channels_category(self, ctx):
        await ctx.send("Укажите ID категории для временных `голосовых` каналов:")
        category_id = await self.wait_for_message(ctx)
        category = None
        while not category:
            try:
                category_id = int(category_id.content)
                category = self.bot.get_channel(category_id)
                if not isinstance(category, disnake.CategoryChannel):
                    raise ValueError
            except (ValueError, AttributeError):
                await ctx.send("Категория не найдена, попробуйте ещё раз:")
                category_id = await self.wait_for_message(ctx)

        query = "INSERT INTO guild_settings (guild_id, voice_channel_category_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET voice_channel_category_id = $2"

        await self.save_settings(query, ctx.guild.id, category_id)
        await OnJoinChannel.unload_guild_settings(self.bot, ctx.guild.id)


        bot_overwrite = disnake.PermissionOverwrite(
            view_channel=True,
            manage_permissions=True,
            manage_channels=True
        )
        voice_channel = await ctx.guild.create_voice_channel(
            name="【➕】Создать",
            category=category,
            overwrites=category.overwrites
        )
        bot = ctx.guild.get_member(self.bot.user.id)
        await voice_channel.set_permissions(bot, overwrite=bot_overwrite)

        query = "INSERT INTO guild_settings (guild_id, create_voice_channel_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET create_voice_channel_id = $2"

        await self.save_settings(query, ctx.guild.id, voice_channel.id)

    async def ask_text_channels_category(self, ctx):
        await ctx.send("Укажите ID категории для временных `текстовых` каналов:")
        text_channels_category_id = await self.wait_for_message(ctx)
        text_channels_category = None

        while not text_channels_category:
            try:
                text_channels_category_id = int(text_channels_category_id.content)
                text_channels_category = self.bot.get_channel(text_channels_category_id)
            except (ValueError, AttributeError):
                await ctx.send("Канал не найден, попробуйте ещё раз:")
                text_channels_category_id = await self.wait_for_message(ctx)

        query = "INSERT INTO guild_settings (guild_id, text_channel_category_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET text_channel_category_id = $2"

        await self.save_settings(query, ctx.guild.id, text_channels_category_id)

    async def ask_art_channel_id(self, ctx):
        await ctx.send("Укажите ID канала для артов:")
        art_channel_id = await self.wait_for_message(ctx)
        art_channel = None

        while not art_channel:
            try:
                art_channel_id = int(art_channel_id.content)
                art_channel = self.bot.get_channel(art_channel_id)
            except (ValueError, AttributeError):
                await ctx.send("Канал не найден, попробуйте ещё раз:")
                art_channel_id = await self.wait_for_message(ctx)

        query = "INSERT INTO guild_settings (guild_id, art_channel_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET art_channel_id = $2"

        await self.save_settings(query, ctx.guild.id, art_channel_id)

    async def ask_meme_channel_id(self, ctx):
        await ctx.send("Укажите ID канала для мемов:")
        meme_channel_id = await self.wait_for_message(ctx)
        meme_channel = None

        while not meme_channel:
            try:
                meme_channel_id = int(meme_channel_id.content)
                meme_channel = self.bot.get_channel(meme_channel_id)
            except (ValueError, AttributeError):
                await ctx.send("Канал не найден, попробуйте ещё раз:")
                meme_channel_id = await self.wait_for_message(ctx)

        query = "INSERT INTO guild_settings (guild_id, meme_channel_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET meme_channel_id = $2"

        await self.save_settings(query, ctx.guild.id, meme_channel_id)

    async def ask_roles_mention_in_tickets(self, ctx):
        await ctx.send("Укажите ID ролей, которые будут иметь доступ к тикетам, через пробел:")
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

        query = "INSERT INTO guild_settings (guild_id, roles_id_to_mention)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET roles_id_to_mention = $2"

        await self.save_settings(query, ctx.guild.id, roles_id)

    async def ask_button_cooldown(self, ctx):
        await ctx.send("Укажите время (в минутах) между нажатем кнопок для одного пользователя (Изначально 5 минут):")
        input_cooldown = await self.wait_for_message(ctx)
        cooldown = None
        while type(cooldown) != int:
            try:
                cooldown = int(input_cooldown.content)
            except (ValueError, AttributeError):
                await ctx.send("Введите только число:")
                input_cooldown = await self.wait_for_message(ctx)
                cooldown = None

        query = "INSERT INTO guild_settings (guild_id, button_cooldown)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET button_cooldown = $2"

        await self.save_settings(query, ctx.guild.id, cooldown)


    @commands.slash_command()
    async def setup_creative_work(self, ctx: disnake.CommandInteraction):
        """Указать каналы для артов и мемов"""
        await self.ask_art_channel_id(ctx)
        await self.ask_meme_channel_id(ctx)

        await ctx.send("Настройки сохранены", ephemeral=True)

    @commands.slash_command()
    async def setup_voice(self, ctx: disnake.CommandInteraction):
        """Указать ID категории для временных каналов"""
        await self.ask_voice_channels_category(ctx)

        await ctx.send("Настройки сохранены", ephemeral=True)

    @commands.slash_command()
    async def setup_tickets(self, ctx: disnake.CommandInteraction):
        """Указать категорию для тикетов и роли, которые будут иметь доступ к тикетам"""
        await self.ask_text_channels_category(ctx)
        await self.ask_roles_mention_in_tickets(ctx)
        await self.ask_button_cooldown(ctx)

        await ctx.send("Настройки сохранены", ephemeral=True)

    @commands.slash_command()
    async def setup_all(self, ctx: disnake.CommandInteraction):
        """Настроить всё сразу"""
        await self.ask_art_channel_id(ctx)
        await self.ask_meme_channel_id(ctx)

        await self.ask_text_channels_category(ctx)
        await self.ask_roles_mention_in_tickets(ctx)
        await self.ask_button_cooldown(ctx)

        await self.ask_voice_channels_category(ctx)

        await ctx.send("Настройка успешно завершена", ephemeral=True)

    @commands.slash_command()
    async def edit_art_channel(self, ctx: disnake.CommandInteraction):
        """Изменить ID канала для артов"""
        await self.ask_art_channel_id(ctx)
        await ctx.send("Настройки изменены", ephemeral=True)

    @commands.slash_command()
    async def edit_meme_channel(self, ctx: disnake.CommandInteraction):
        """Изменить ID канала для мемов"""
        await self.ask_meme_channel_id(ctx)
        await ctx.send("Настройки изменены", ephemeral=True)

    @commands.slash_command()
    async def edit_text_channels_category(self, ctx: disnake.CommandInteraction):
        """Изменить ID категории для создаваемых тикетов"""
        await self.ask_text_channels_category(ctx)
        await ctx.send("Настройки изменены", ephemeral=True)

    @commands.slash_command()
    async def edit_roles_mention(self, ctx: disnake.CommandInteraction):
        """Изменить ID ролей для упоминания при создании тикетов"""
        await self.ask_roles_mention_in_tickets(ctx)
        await ctx.send("Настройки изменены", ephemeral=True)

    @commands.slash_command()
    async def edit_button_cooldown(self, ctx: disnake.CommandInteraction):
        """Изменить кулдаун нажатия на кнопку для каждого пользователя"""
        await self.ask_button_cooldown(ctx)
        await ctx.send("Настройки изменены", ephemeral=True)

    @commands.slash_command()
    async def edit_voice_channels_category(self, ctx: disnake.CommandInteraction):
        """Изменить ID категории для голосовых каналов"""
        await self.ask_voice_channels_category(ctx)
        await ctx.send("Настройки изменены", ephemeral=True)



def setup(bot):
    bot.add_cog(SetupBot(bot))
    # bot.add_cog(TextChannel(bot))
