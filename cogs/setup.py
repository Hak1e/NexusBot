import disnake
from disnake.ext import commands
import os
from dotenv import load_dotenv
from core.bot import Nexus
import asyncpg

load_dotenv()

MAX_VIEWS_IN_MENU = 25
MAX_BUTTONS_COUNT = 5

class SelectRoles(disnake.ui.Select):
    def __init__(self, roles, row):
        options = []
        for role in roles:
            options.append(disnake.SelectOption(label=role.name, value=str(role.id)))
        super().__init__(
            placeholder=f"{row} часть. Выберите роли",
            min_values=1,
            max_values=len(roles),
            options=options
        )

        self.roles = []

    async def callback(self, interaction: disnake.MessageInteraction):
        if not interaction.values:
            await interaction.response.defer()
        else:
            roles = [f"<@&{role_id}>" for role_id in interaction.values]
            for role in roles:
                self.roles.append(role)
            await interaction.response.send_message(f"Вы выбрали {', '.join(roles)}", ephemeral=True)


class TextChannel(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.bot.settings = {}


    # @commands.slash_command()
    async def test(
            self,
            ctx: disnake.CommandInteraction,
            roles_reverse: bool = False
    ):
        """Настройки временного канала. Выбор ролей для доступа к временному каналу
        Parameters
        ----------
        ctx: command interaction
        roles_reverse: сортировка ролей. По стандарту(False) роли снизу вверх
        """
        def check(msg):
            return msg.author.id == ctx.author.id and msg.channel == ctx.channel



        roles = ctx.guild.roles
        if roles_reverse:
            roles.reverse()
        role_chunks = [roles[i:i+MAX_VIEWS_IN_MENU] for i in range(0, len(roles), MAX_VIEWS_IN_MENU)]
        view = disnake.ui.View(timeout=None)

        chunks_number = 0
        for _ in role_chunks:
            chunks_number += 1

        loop_run_times = 1 # если чанков < 5, цикл отработает всего 1 раз
        if chunks_number > 5:
            loop_run_times = chunks_number // MAX_BUTTONS_COUNT + 1

        row = 1
        chunk_position = 0
        messages = []
        while loop_run_times > 0:
            while chunk_position <= len(role_chunks):
                current_number_of_buttons = len(view.children)

                if chunk_position == len(role_chunks):
                    messages.append(await ctx.channel.send(view=view))
                    loop_run_times -= 1

                elif current_number_of_buttons < MAX_BUTTONS_COUNT:
                    view.add_item(SelectRoles(role_chunks[chunk_position], row))
                    row += 1

                else:
                    messages.append(await ctx.channel.send(view=view))
                    loop_run_times -= 1
                    view = disnake.ui.View(timeout=None)
                    break

                chunk_position += 1

        async def delete_messages(messages):
            for message in messages:
                await message.delete()

        await ctx.send("Введите `next`, чтобы продолжить:")
        user_input = await self.bot.wait_for("message", check=check)
        if user_input == "next":
            try:
                await delete_messages(messages)
            except Exception as e:
                await ctx.channel.send(f"Не удалось удалить предыдущие сообщения.\nОшибка: {e}")


        await ctx.send("Конец настройки")



class SetupBot(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.get_pool()


    async def save_voice_settings(
            self,
            guild_id: int,
            category_id: int,
            voice_channel_id: int
    ):
        async with self.pool.acquire() as conn:
            query = "INSERT INTO guild_settings (guild_id, temp_voice_channel_category_id, temp_create_voice_channel)" \
                    "VALUES ($1, $2, $3)" \
                    "ON CONFLICT (guild_id) DO UPDATE SET temp_voice_channel_category_id = $2, temp_create_voice_channel = $3"
            await conn.execute(query, guild_id, category_id, voice_channel_id)
            print(f"Настройки сохранены")

    async def save_text_settings(
            self,
            guild_id: int,
            art_channel_id: int,
            meme_channel_id: int
    ):
        async with self.pool.acquire() as conn:
            query = "INSERT INTO guild_settings (guild_id, art_channel_id, meme_channel_id)" \
                    "VALUES ($1, $2, $3)" \
                    "ON CONFLICT (guild_id) DO UPDATE SET art_channel_id = $2, meme_channel_id = $3"
            await conn.execute(query, guild_id, art_channel_id, meme_channel_id)
            print(f"Настройки сохранены")
    @commands.slash_command()
    async def setup_voice(self, ctx: disnake.CommandInteraction):
        def check(msg):
            return msg.author.id == ctx.author.id and msg.channel == ctx.channel

        await ctx.send("Укажите ID категории для временных каналов:")
        category_id = await self.bot.wait_for("message", check=check)
        category = None

        while not category:
            try:
                category_id = int(category_id.content)
                category = self.bot.get_channel(category_id)
                if not isinstance(category, disnake.CategoryChannel):
                    raise ValueError
            except (ValueError, AttributeError):
                await ctx.send("Категория не найдена, попробуйте ещё раз:")
                category_id = await self.bot.wait_for("message", check=check)


        await ctx.send("Укажите ID голосового канала:")
        voice_channel_id = await self.bot.wait_for("message", check=check)
        voice_channel = None

        while not voice_channel:
            try:
                voice_channel_id = int(voice_channel_id.content)
                voice_channel = self.bot.get_channel(voice_channel_id)
                if not isinstance(voice_channel, disnake.VoiceChannel):
                    raise ValueError
            except (ValueError, AttributeError):
                await ctx.send("Категория не найдена, попробуйте ещё раз:")
                voice_channel_id = await self.bot.wait_for("message", check=check)


        await self.save_voice_settings(ctx.guild.id, category_id, voice_channel_id)
        await ctx.send("Настройки сохранены", ephemeral=True)

    @commands.slash_command()
    async def setup_art_meme_channels(self, ctx: disnake.CommandInteraction):
        def check(msg):
            return msg.author.id == ctx.author.id and msg.channel == ctx.channel

        await ctx.send("Укажите ID канала для артов:")
        art_channel_id = await self.bot.wait_for("message", check=check)
        art_channel = None

        while not art_channel:
            try:
                art_channel_id = int(art_channel_id.content)
                art_channel = self.bot.get_channel(art_channel_id)
            except (ValueError, AttributeError):
                await ctx.send("Канал не найден, попробуйте ещё раз:")
                art_channel_id = await self.bot.wait_for("message", check=check)


        await ctx.send("Укажите ID канала для мемов:")
        meme_channel_id = await self.bot.wait_for("message", check=check)
        meme_channel = None

        while not meme_channel:
            try:
                meme_channel_id = int(meme_channel_id.content)
                meme_channel = self.bot.get_channel(meme_channel_id)
            except (ValueError, AttributeError):
                await ctx.send("Канал не найден, попробуйте ещё раз:")
                meme_channel_id = await self.bot.wait_for("message", check=check)


        await self.save_text_settings(ctx.guild.id, art_channel_id, meme_channel_id)
        await ctx.send("Настройки сохранены", ephemeral=True)

def setup(bot):
    bot.add_cog(SetupBot(bot))
    bot.add_cog(TextChannel(bot))
