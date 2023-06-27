import asyncpg
import disnake
from disnake.ext import commands
import config
import json
from core.bot import Nexus
import typing as t

file_name = "settings.json"
class CloseButton(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(
        label="Закрыть тикет",
        style=disnake.ButtonStyle.red,
        custom_id="delete_channel_button",
        emoji="❌"
    )
    async def delete_channel_button(
            self,
            button: disnake.ui.Button,
            ctx: disnake.MessageInteraction
    ):
        channel = ctx.channel
        await channel.delete()


class ButtonView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # право на управление каналами, ролями
    async def create_temp_channel(
            self,
            ctx: disnake.MessageInteraction,
            roles: list,
            ping_roles: str,
            channel_name: str
    ):
        guild = ctx.guild
        user = ctx.author
        category = guild.get_channel(config.text_channel_category_id)

        user_overwrite = disnake.PermissionOverwrite()
        user_overwrite.send_messages = True
        user_overwrite.view_channel = True

        overwrites = {
            guild.default_role: disnake.PermissionOverwrite(read_messages=False),
            ctx.message.author: user_overwrite,
            user: user_overwrite,
        }

        for role in roles:
            overwrites[role] = user_overwrite

        channel = await guild.create_text_channel(
            name=f"{user}-{channel_name}",
            category=category,
            overwrites=overwrites
        )

        embed = disnake.Embed(description=f"Чтобы закрыть тикет, нажмите кнопку ниже")
        view = CloseButton()

        await channel.send(
            embed=embed,
            view=view
        )
        await channel.send(ping_roles)
        await ctx.response.defer()

    @disnake.ui.button(
        label="Вопрос",
        style=disnake.ButtonStyle.grey,
        custom_id="question_button",
        emoji="❔"
    )
    async def question_button(
            self,
            button: disnake.ui.Button,
            ctx: disnake.MessageInteraction
    ):
        support_roles = [ctx.guild.get_role(role_id) for role_id in config.add_role_to_question]
        moderation_roles = [ctx.guild.get_role(role_id) for role_id in config.add_role_to_report]
        roles_to_mention = support_roles + moderation_roles

        ping_roles = ""
        for role in roles_to_mention:
            ping_roles += f"<@&{role.id}>, "
        ping_roles += f"у <@{ctx.author.id}> имеется вопрос"

        await self.create_temp_channel(
            ctx=ctx,
            roles=roles_to_mention,
            ping_roles=ping_roles,
            channel_name="вопрос"
        )

    @disnake.ui.button(
        label="Жалоба",
        style=disnake.ButtonStyle.red,
        custom_id="report_button",
        emoji="❕"
    )
    async def report_button(
            self,
            button: disnake.ui.Button,
            ctx: disnake.MessageInteraction
    ):
        moderation_roles = [ctx.guild.get_role(role_id) for role_id in config.add_role_to_report]

        ping_roles = ""
        for role in moderation_roles:
            ping_roles += f"<@&{role.id}>, "
        ping_roles += f"жалоба от  <@{ctx.author.id}>"

        await self.create_temp_channel(
            ctx=ctx,
            roles=moderation_roles,
            ping_roles=ping_roles,
            channel_name="жалоба"
        )

    @disnake.ui.button(
        label="Предложение",
        style=disnake.ButtonStyle.blurple,
        custom_id="offer_button",
        emoji="📝"
    )
    async def offer_button(
            self,
            button: disnake.ui.Button,
            ctx: disnake.MessageInteraction
    ):
        moderation_roles = [ctx.guild.get_role(role_id) for role_id in config.add_role_to_report]

        ping_roles = ""
        for role in moderation_roles:
            ping_roles += f"<@&{role.id}>, "
        ping_roles += f"<@{ctx.author.id}> хочет что-то предложить!"

        await self.create_temp_channel(
            ctx=ctx,
            roles=moderation_roles,
            ping_roles=ping_roles,
            channel_name="предложение"
        )


class EmbedButtons(commands.Cog):
    def __init__(
            self,
            bot: Nexus
    ):
        self.bot = bot
        self.persistent_views_added = False
        self.pool: t.Optional[asyncpg.Pool] = None
        self.message_id = self.load_settings()
        self.bot.settings = {}

    async def load_settings(self):
        async with self.pool.acquire() as conn:
            query = "SELECT message_with_buttons_id FROM guild_settings WHERE guild_id = $1"
            result = await conn.fetchval(query, self.bot.guild.id)
            print(f"Настройки загружены: {result}")
            return result

        # try:
        #     with open("file_name", "r") as f:
        #         self.bot.settings = json.load(f)
        #         self.message_id = self.bot.settings.get("message_id")
        #
        #     print(f"Message id: {self.message_id}")
        #
        # except FileNotFoundError:
        #     print("Файл settings.json не найден. Он будет создан при создании сообщения")
        # except:
        #     print("Ошибка при чтении файла settings.json")

    async def save_settings(
            self,
            guild_id: int,
            message_id: int
    ):
        async with self.pool.acquire() as conn:
            query = "INSERT INTO guild_settings (guild_id, message_with_buttons_id)" \
                    "VALUES ($1, $2)" \
                    "ON CONFLICT (guild_id) DO UPDATE SET message_with_buttons_id = $2"
            await conn.execute(query, guild_id, message_id)
            print(f"Настройки сохранены")


    @commands.slash_command()
    async def support(
            self,
            ctx: disnake.CommandInteraction,
            image: disnake.Attachment = None
    ):
        """Создать embed с кнопками
        Parameters
        ----------
        ctx: command interaction
        image: добавить изображение (отдельным сообщением). Рекомендуется для большей привлекательности
        """
        view = ButtonView()
        embeds = []
        if image:
            embed1 = (
                disnake.Embed(
                    description="",
                    color=0x3f8fdf,
                )
                .set_image(image)
            )
            embeds.append(embed1)

        embed2 = (
            disnake.Embed(
                description="Воспользовавшись кнопками ниже можно написать модераторам по интересующим темам:",
                color=0x3f8fdf
            )
            .set_image(
                url="https://media.discordapp.net/attachments/1015290335779364958/1015295923829608468/unknown.png")
        )
        embeds.append(embed2)
        message = await ctx.channel.send(embeds=embeds, view=view)

        # data = {"message_id": message.id}
        # with open("file_name", "w") as f:
        #     json.dump(data, f)

        await self.save_settings(ctx.guild.id, message.id)


        await ctx.send("Создан embed с кнопками")

    @commands.Cog.listener()
    async def on_connect(self):
        print("On_connect в классе с кнопками!")
        if self.persistent_views_added:
            return

        self.bot.add_view(ButtonView(), message_id=self.message_id)
        # self.bot.add_view(ButtonView(), message_id=1121460668558737442)


def setup(bot):
    bot.add_cog(EmbedButtons(bot))
