import disnake
from disnake.ext import commands
from disnake import SelectOption
import os
from dotenv import load_dotenv
from core.bot import Nexus
import asyncpg

load_dotenv()

MAX_VIEWS_IN_MENU = 25
MAX_BUTTONS_COUNT = 5


class NextButton(disnake.ui.View):
    def __init__(self, view_list):
        super().__init__(timeout=None)
        self.view_list = view_list


    @disnake.ui.button(
        label="Next",
        style=disnake.ButtonStyle.primary,
        custom_id="next_button",
    )
    async def next(
            self,
            button: disnake.ui.Button,
            ctx: disnake.MessageInteraction,
    ):
        all_selected_roles = []

        for view in self.view_list:
            for child in view.children:
                if isinstance(child, SelectRoles):
                    all_selected_roles.extend([f"<@&{role_id}>" for role_id in child.selected_roles_id])
        await ctx.send(f"Вы выбрали {', '.join(all_selected_roles)}", ephemeral=True)


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


class TextChannel(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.bot.settings = {}

    @commands.slash_command()
    async def select_roles(
            self,
            ctx: disnake.CommandInteraction,
            roles_reverse: bool = False
    ):
        """Настройки временного канала. Выбор ролей для доступа к временному текстовому каналу
        Parameters
        ----------
        ctx: command ctx
        roles_reverse: сортировка ролей. По стандарту(False) роли снизу вверх
        """
        await ctx.send("Выберите роли, которые будут получать уведомление при создании тикета:")


        def check(msg):
            return msg.author.id == ctx.author.id and msg.channel == ctx.channel

        roles = ctx.guild.roles
        if roles_reverse:
            roles.reverse()
        role_chunks = [roles[i:i + MAX_VIEWS_IN_MENU - 1] for i in range(0, len(roles), MAX_VIEWS_IN_MENU)]
        view = disnake.ui.View(timeout=None)

        loop_run_times = 1  # если чанков < 5, цикл отработает всего 1 раз
        if len(role_chunks) > 5:
            loop_run_times = len(role_chunks) // MAX_BUTTONS_COUNT + 1

        row = 1
        chunk_position = 0
        view_list = []

        while loop_run_times > 0:
            while chunk_position <= len(role_chunks):
                current_number_of_buttons = len(view.children)

                if chunk_position == len(role_chunks):
                    await ctx.channel.send(view=view)
                    view_list.append(view)
                    loop_run_times -= 1

                elif current_number_of_buttons < MAX_BUTTONS_COUNT:
                    view.add_item(SelectRoles(role_chunks[chunk_position], row))
                    row += 1

                else:
                    await ctx.channel.send(view=view)
                    view_list.append(view)
                    loop_run_times -= 1
                    view = disnake.ui.View(timeout=None)
                    break

                chunk_position += 1

        def check(msg):
            return msg.author.id == ctx.author.id and msg.channel == ctx.channel


        view_button = NextButton(view_list)

        message = await ctx.channel.send("Нажмите кнопку ниже для продолжения", view=view_button)


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
        await ctx.send("Укажите ID категории для временных каналов:")
        category_id = await self.wait_for_message(ctx)
        category = None
        print(f"Inputted category id: {category_id}\n It's type: {type(category_id)}")
        while not category:
            try:
                category_id = int(category_id.content)
                category = self.bot.get_channel(category_id)
                if not isinstance(category, disnake.CategoryChannel):
                    raise ValueError
            except (ValueError, AttributeError):
                await ctx.send("Категория не найдена, попробуйте ещё раз:")
                category_id = await self.wait_for_message(ctx)

        query = "INSERT INTO guild_settings (guild_id, temp_voice_channel_category_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO UPDATE SET temp_voice_channel_category_id = $2"

        await self.save_settings(query, ctx.guild.id, category_id)

    async def ask_text_channels_category(self, ctx):
        await ctx.send("Укажите ID категории для временных текстовых каналов:")
        text_channels_category_id = await self.wait_for_message(ctx)
        text_channels_category = None

        while not text_channels_category:
            try:
                text_channels_category_id = int(text_channels_category_id.content)
                text_channels_category = self.bot.get_channel(text_channels_category_id)
            except (ValueError, AttributeError):
                await ctx.send("Канал не найден, попробуйте ещё раз:")
                text_channels_category_id = await self.wait_for_message(ctx)

        query = "INSERT INTO guild_settings (guild_id, temp_text_channel_category_id)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO UPDATE SET temp_text_channel_category_id = $2"

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
                "ON CONFLICT (guild_id) DO UPDATE SET art_channel_id = $2"

        await self.save_settings(query, ctx.guild.id, art_channel_id)

    async def ask_create_voice_channel_id(self, ctx):
        await ctx.send("Укажите ID голосового канала:")
        voice_channel_id = await self.wait_for_message(ctx)
        voice_channel = None

        while not voice_channel:
            try:
                voice_channel_id = int(voice_channel_id.content)
                voice_channel = self.bot.get_channel(voice_channel_id)
                if not isinstance(voice_channel, disnake.VoiceChannel):
                    raise ValueError
            except (ValueError, AttributeError):
                await ctx.send("Категория не найдена, попробуйте ещё раз:")
                voice_channel_id = await self.wait_for_message(ctx)

        query = "INSERT INTO guild_settings (guild_id, temp_create_voice_channel)" \
                "VALUES ($1, $2)" \
                "ON CONFLICT (guild_id) DO UPDATE SET temp_create_voice_channel = $2"

        await self.save_settings(query, ctx.guild.id, voice_channel_id)

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
                "ON CONFLICT (guild_id) DO UPDATE SET meme_channel_id = $2"

        await self.save_settings(query, ctx.guild.id, meme_channel_id)

    @commands.slash_command()
    async def setup_text(self, ctx: disnake.CommandInteraction):
        """Указать категорию для временных текстовых каналов, каналы для артов и мемов"""
        await self.ask_text_channels_category(ctx)
        await self.ask_art_channel_id(ctx)
        await self.ask_meme_channel_id(ctx)

        await ctx.send("Настройки сохранены", ephemeral=True)

    @commands.slash_command()
    async def setup_voice(self, ctx: disnake.CommandInteraction):
        """Указать категорию и ID голосового канала для временных каналов"""
        await self.ask_voice_channels_category(ctx)
        await self.ask_create_voice_channel_id(ctx)

        await ctx.send("Настройки сохранены", ephemeral=True)

    # @commands.slash_command()
    async def setup_all(self, ctx: disnake.CommandInteraction):
        pass


def setup(bot):
    bot.add_cog(SetupBot(bot))
    bot.add_cog(TextChannel(bot))
