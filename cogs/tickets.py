import asyncpg
import disnake
from disnake.ext import commands
from core.bot import Nexus
from datetime import datetime, timedelta


class ButtonView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Вопрос", style=disnake.ButtonStyle.grey,
                       custom_id="question_button", emoji="❔")
    async def question_button(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        pass

    @disnake.ui.button(label="Жалоба", style=disnake.ButtonStyle.red,
                       custom_id="report_button", emoji="❕")
    async def report_button(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        pass

    @disnake.ui.button(label="Предложение", style=disnake.ButtonStyle.blurple,
                       custom_id="offer_button", emoji="📝")
    async def offer_button(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        pass


class Tickets(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool: asyncpg.Pool = self.bot.get_pool()
        self.category_id = None
        self.roles_id_to_mention = []
        self.guild_button_cooldown = None
        self.guild_button_cooldown_end_time = None
        self.guild_category_ids = None
        self.guild_mention_roles_ids = None

    async def create_ticket_channel(self, ctx: disnake.MessageInteraction, roles: list,
                                    ping_roles: str, channel_name: str):
        guild = ctx.guild
        user = ctx.author
        category = ctx.guild.get_channel(self.guild_category_ids)
        user_overwrite = disnake.PermissionOverwrite(send_messages=True, view_channel=True)

        overwrites = {
            guild.default_role: disnake.PermissionOverwrite(read_messages=False),
            ctx.message.author: user_overwrite,
            user: user_overwrite,
        }

        for role in roles:
            overwrites[role] = user_overwrite

        channel = await guild.create_text_channel(name=f"{user}-{channel_name}", category=category,
                                                  overwrites=overwrites)
        embed = disnake.Embed(description=f"Чтобы закрыть тикет, нажмите кнопку ниже")

        await channel.send(
            embed=embed,
            components=[
                disnake.ui.Button(label="Закрыть тикет", style=disnake.ButtonStyle.red,
                                  custom_id="delete_channel_button", emoji="❌")
            ]
        )
        allowed_mentions = disnake.AllowedMentions(users=True, roles=True)

        await channel.send(ping_roles, allowed_mentions=allowed_mentions)
        await ctx.response.defer()

    async def get_roles_and_text(self, ctx, message):
        roles_to_add = [ctx.guild.get_role(role_id) for role_id in self.guild_mention_roles_ids]
        roles_to_mention = ""
        for role in roles_to_add:
            roles_to_mention += f"{role.mention}, "
        roles_to_mention += message
        return roles_to_add, roles_to_mention

    async def question_channel(self, ctx):
        roles_to_add, roles_to_mention = \
            await self.get_roles_and_text(ctx, f"вопрос от {ctx.author.mention}")
        await self.create_ticket_channel(ctx=ctx, roles=roles_to_add,
                                         ping_roles=roles_to_mention, channel_name="вопрос")

    async def report_channel(self, ctx):
        roles_to_add, roles_to_mention = \
            await self.get_roles_and_text(ctx, f"жалоба от {ctx.author.mention}")
        await self.create_ticket_channel(ctx=ctx, roles=roles_to_add,
                                         ping_roles=roles_to_mention, channel_name="жалоба")

    async def offer_channel(self, ctx):
        roles_to_add, roles_to_mention = \
            await self.get_roles_and_text(ctx, f"{ctx.author.mention} хочет что-то предложить")

        await self.create_ticket_channel(ctx=ctx, roles=roles_to_add,
                                         ping_roles=roles_to_mention, channel_name="предложение")

    async def activate_cooldown(self, ctx):
        self.guild_button_cooldown_end_time = datetime.now() + self.guild_button_cooldown
        self.guild_button_cooldown_end_time.isoformat()
        query = "INSERT INTO cooldown (guild_id, user_id, button_cooldown_end_time) " \
                "VALUES ($1, $2, $3) " \
                "ON CONFLICT (guild_id) DO " \
                "UPDATE SET user_id = $2, button_cooldown_end_time = $3"
        await self.pool.execute(query, ctx.guild.id, ctx.author.id, self.guild_button_cooldown_end_time)

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        button_id = ctx.component.custom_id
        guild_id = ctx.guild.id

        if button_id == "delete_channel_button":
            await ctx.channel.delete()
            return

        class_buttons_ids = ["question_button", "report_button", "offer_button"]
        if button_id not in class_buttons_ids:
            return

        try:
            query = "SELECT tickets_category_id " \
                    "FROM guild_settings " \
                    "WHERE guild_id = $1"
            self.guild_category_ids = await self.pool.fetchval(query, guild_id)

            query = "SELECT roles_id_to_mention " \
                    "FROM text_channels " \
                    "WHERE guild_id = $1"
            self.guild_mention_roles_ids = list(await self.pool.fetchval(query, guild_id))

            query = "SELECT button_cooldown " \
                    "FROM cooldown " \
                    "WHERE guild_id = $1"
            self.guild_button_cooldown = await self.pool.fetchval(query, guild_id)
            self.guild_button_cooldown = timedelta(minutes=self.guild_button_cooldown)

        except:
            await ctx.send(
                "Настройки для сервера не найдены. Обратитесь к администратору для настройки", ephemeral=True
            )

        cooldown_active = False
        response = ""

        query = "SELECT button_cooldown_end_time " \
                "FROM cooldown " \
                "WHERE guild_id = $1 and user_id = $2"

        row = await self.pool.fetchrow(query, ctx.guild.id, ctx.author.id)
        if row:
            self.guild_button_cooldown_end_time = row["button_cooldown_end_time"]
            tz_time = datetime.now().astimezone(self.guild_button_cooldown_end_time.tzinfo)

            if self.guild_button_cooldown_end_time and \
                    self.guild_button_cooldown_end_time > tz_time:
                remaining_time = self.guild_button_cooldown_end_time - tz_time
                remaining_time = str(remaining_time).split(".")[0]
                response = f"Вы сможете нажать на кнопку ещё раз через {remaining_time} (часы:минуты:секунды)"
                cooldown_active = True

        if cooldown_active:
            await ctx.send(response, ephemeral=True)
        else:
            try:
                match button_id:
                    case "question_button":
                        await self.question_channel(ctx)
                    case "report_button":
                        await self.report_channel(ctx)
                    case "offer_button":
                        await self.offer_channel(ctx)

                await self.activate_cooldown(ctx)
            except:
                await ctx.send("Не могу создать канал. Нет доступа к категории тикетов", ephemeral=True)

    @commands.slash_command()
    async def create(self, ctx):
        pass

    @create.sub_command()
    async def tickets_creator(self, ctx: disnake.CommandInteraction, image_url: str = None):
        """Создать embed с кнопками
        Parameters
        ----------
        ctx: command interaction
        image_url: Добавить изображение
        """
        view = ButtonView()
        embeds = []
        if image_url:
            embed1 = (
                disnake.Embed(
                    description="",
                    color=0x3f8fdf,
                )
                .set_image(url=image_url)
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
        try:
            await ctx.channel.send(embeds=embeds, view=view)
            await ctx.send("Создан embed с кнопками", ephemeral=True)
        except:
            await ctx.send("Не удалось отправить сообщение.\n"
                           "Убедитесь, что я могу:"
                           "Просматривать канал\n"
                           "Отправлять сообщения\n"
                           "Встраивать ссылки\n"
                           )

    async def is_ticket(self, ctx):
        query = "SELECT tickets_category_id " \
                "FROM guild_settings " \
                "WHERE guild_id = $1"
        category_id = await self.pool.fetchval(query, ctx.guild.id)

        if ctx.channel.category.id == category_id:
            return True
        else:
            return False

    async def member_overwrite(self, ctx, member, overwrite, message):
        if await self.is_ticket(ctx):
            await ctx.channel.set_permissions(member, overwrite=overwrite)
            await ctx.send(message)
        else:
            await ctx.send("Вы можете использовать эту команду только в тикетах", ephemeral=True)

    @commands.slash_command()
    async def user(self, ctx):
        pass

    @user.sub_command()
    async def add(self, ctx: disnake.CommandInteraction, member: disnake.Member):
        """Добавить участника в этот канал"""
        overwrite = disnake.PermissionOverwrite(view_channel=True)
        message = f"Пользователь {member.mention} добавлен в этот чат"
        await self.member_overwrite(ctx, member, overwrite, message)

    @user.sub_command()
    async def remove(self, ctx: disnake.CommandInteraction, member: disnake.Member):
        """Удалить участника из этого канала"""
        message = f"Пользователь {member.mention} удалён из этого чата"
        await self.member_overwrite(ctx, member, None, message)


def setup(bot):
    bot.add_cog(Tickets(bot))
