import asyncpg
import disnake
from disnake.ext import commands
from core.bot import Nexus
from datetime import datetime, timedelta
import asyncio

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
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool: asyncpg.Pool = self.bot.get_pool()
        self.category_id = None
        self.roles_id_to_mention = []
        self.guild_settings_loaded = {}
        self.button_cooldown = timedelta(minutes=5)
        self.button_cooldown_end_time = timedelta(seconds=0)

    async def create_ticket_channel(
            self,
            ctx: disnake.MessageInteraction,
            roles: list,
            ping_roles: str,
            channel_name: str
    ):
        guild = ctx.guild
        user = ctx.author
        category = ctx.guild.get_channel(self.category_id)
        user_overwrite = disnake.PermissionOverwrite(
            send_messages=True,
            view_channel=True
        )


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

        await channel.send(
            embed=embed,
            components=[
                disnake.ui.Button(
                    label="Закрыть тикет",
                    style=disnake.ButtonStyle.red,
                    custom_id="delete_channel_button",
                    emoji="❌"
                )
            ]
        )
        allowed_mentions = disnake.AllowedMentions(
            users=True,
            roles=True
        )

        await channel.send(ping_roles, allowed_mentions=allowed_mentions)
        # await ctx.response.defer() - на локальной БД здесь всё было норм

    async def get_roles_and_text(self, ctx, message):
        roles_to_add = [ctx.guild.get_role(role_id) for role_id in self.roles_id_to_mention]
        roles_to_mention = ""
        for role in roles_to_add:
            roles_to_mention += f"{role.mention}, "
        roles_to_mention += message
        return roles_to_add, roles_to_mention

    async def question_channel(self, ctx):
        roles_to_add, roles_to_mention = \
            await self.get_roles_and_text(ctx, f"вопрос от {ctx.author.mention}")
        await self.create_ticket_channel(
            ctx=ctx,
            roles=roles_to_add,
            ping_roles=roles_to_mention,
            channel_name="вопрос"
        )

    async def report_channel(self, ctx):
        roles_to_add, roles_to_mention = \
            await self.get_roles_and_text(ctx, f"жалоба от {ctx.author.mention}")
        await self.create_ticket_channel(
            ctx=ctx,
            roles=roles_to_add,
            ping_roles=roles_to_mention,
            channel_name="жалоба"
        )

    async def offer_channel(self, ctx):
        roles_to_add, roles_to_mention = \
            await self.get_roles_and_text(ctx, f"{ctx.author.mention} хочет что-то предложить")

        await self.create_ticket_channel(
            ctx=ctx,
            roles=roles_to_add,
            ping_roles=roles_to_mention,
            channel_name="предложение"
        )

    async def activate_cooldown(self, ctx):
        self.button_cooldown_end_time = datetime.now() + self.button_cooldown
        self.button_cooldown_end_time.isoformat()
        # TODO: изменена БД. Добавить в кулдаун айди гильдии
        query = "INSERT INTO cooldowns (user_id, button_cooldown_end_time) " \
                "VALUES ($1, $2) " \
                "ON CONFLICT (user_id) DO " \
                "UPDATE SET button_cooldown_end_time = $2"
        await self.pool.execute(query, ctx.author.id, self.button_cooldown_end_time)

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        await ctx.send(f"Ваш тикет скоро будет создан. Пожалуйста, ожидайте", ephemeral=True)

        button_id = ctx.component.custom_id
        guild_id = ctx.guild.id

        if guild_id not in self.guild_settings_loaded:
            self.guild_settings_loaded[guild_id] = False

        if not self.guild_settings_loaded[guild_id]:
            try:

                query = "SELECT tickets_category_id " \
                        "FROM guild_settings " \
                        "WHERE guild_id = $1"
                self.category_id = await self.pool.fetchval(query, guild_id)

                query = "SELECT roles_id_to_mention " \
                        "FROM guild_settings " \
                        "WHERE guild_id = $1"
                self.roles_id_to_mention = await self.pool.fetchval(query, guild_id)

                query = "SELECT button_cooldown " \
                        "FROM guild_settings " \
                        "WHERE guild_id = $1"
                self.button_cooldown = await self.pool.fetchval(query, guild_id)
                self.button_cooldown = timedelta(minutes=self.button_cooldown)

                self.guild_settings_loaded[guild_id] = True
            except:
                await ctx.send(
                    "Настройки для сервера не найдены. Обратитесь к администратору для настройки", ephemeral=True
                )

        if button_id == "delete_channel_button":
            channel = ctx.channel
            await channel.delete()
            return

        cooldown_active = False
        response = ""

        query = "SELECT button_cooldown_end_time " \
                "FROM cooldowns " \
                "WHERE user_id = $1"

        row = await self.pool.fetchrow(query, ctx.author.id)
        if row:
            self.button_cooldown_end_time = row["button_cooldown_end_time"]
            if self.button_cooldown_end_time and \
                    self.button_cooldown_end_time > datetime.now().astimezone(self.button_cooldown_end_time.tzinfo):
                remaining_time = self.button_cooldown_end_time - datetime.now().astimezone(
                    self.button_cooldown_end_time.tzinfo)
                remaining_time = str(remaining_time).split(".")[0]
                response = f"Вы сможете нажать на кнопку ещё раз через {remaining_time} (часы:минуты:секунды)"
                cooldown_active = True

        if cooldown_active:
            await ctx.send(response, ephemeral=True)
        else:
            await self.activate_cooldown(ctx)
            if button_id == "question_button":
                await self.question_channel(ctx)

            elif button_id == "report_button":
                await self.report_channel(ctx)

            elif button_id == "offer_button":
                await self.offer_channel(ctx)


    @commands.slash_command()
    async def create_tickets_creator(
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

    async def member_overwrite(self, ctx, member, overwrite):
        current_category_id = ctx.channel.category.id

        if self.category_id is None:
            query = "SELECT tickets_category_id " \
                    "FROM guild_settings " \
                    "WHERE guild_id = $1"
            self.category_id = await self.pool.fetchval(query, ctx.guild.id)

        if current_category_id == self.category_id:
            await ctx.channel.set_permissions(member, overwrite=overwrite)
        else:
            await ctx.send("Вы можете использовать эту команду только в тикетах", ephemeral=True)

    @commands.slash_command()
    async def add_member(
            self,
            ctx: disnake.CommandInteraction,
            member: disnake.Member
    ):
        """Добавить участника в этот канал"""
        overwrite = disnake.PermissionOverwrite(view_channel=True)
        await self.member_overwrite(ctx, member, overwrite)
        await ctx.send(f"Пользователь {member.mention} добавлен в этот чат")

    @commands.slash_command()
    async def remove_member(
            self,
            ctx: disnake.CommandInteraction,
            member: disnake.Member
    ):
        """Удалить участника из этого канала"""
        overwrite = disnake.PermissionOverwrite(view_channel=True)
        await self.member_overwrite(ctx, member, None)
        await ctx.send(f"Пользователь {member.mention} удалён из этого чата")


def setup(bot):
    bot.add_cog(Tickets(bot))
