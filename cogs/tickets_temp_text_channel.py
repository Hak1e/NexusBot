import asyncpg
import disnake
from disnake.ext import commands
import config
import typing as t
from core.db import Database



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
        pass



class ButtonView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

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
        pass

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
        pass

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
        pass


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = self.bot.get_pool()
        self.message_id = None
        self.channel_id = None

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

        await channel.send(embed=embed, view=view)
        await channel.send(ping_roles)
        await ctx.response.defer()

    async def question_channel(self, ctx):
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
    async def report_channel(self, ctx):
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
    async def offer_channel(self, ctx):
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
    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):

        button_id = ctx.component.custom_id


        if button_id == "question_button":
            await self.question_channel(ctx)

        elif button_id == "report_button":
            await self.report_channel(ctx)

        elif button_id == "offer_button":
            await self.offer_channel(ctx)

        elif button_id == "delete_channel_button":
            channel = ctx.channel
            await channel.delete()




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

        await ctx.send("Создан embed с кнопками", ephemeral=True)


def setup(bot):
    bot.add_cog(Tickets(bot))
