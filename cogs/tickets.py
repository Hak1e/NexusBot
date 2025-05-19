import datetime
import enum

import asyncpg
import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands
from discord.ui import Button, Modal, View


async def send_ticket_log(pool, ctx, title, description, color):
    query = "SELECT logs_channel_id FROM ticket WHERE guild_id = $1"
    logs_channel_id = await pool.fetchval(query, ctx.guild.id)
    if logs_channel_id:
        logs_channel = ctx.guild.get_channel(logs_channel_id)
        embed = discord.Embed(
            title=title, color=color, description=description
        ).set_footer(text="", icon_url=ctx.author.avatar.url)
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await logs_channel.send(embed=embed)


async def get_ticket_number(pool, ctx):
    query = "SELECT number FROM ticket WHERE guild_id = $1"
    return await pool.fetchval(query, ctx.guild.id)


class ButtonsIDs(str, enum.Enum):
    QUESTION = "question_button"
    REPORT = "report_button"
    OFFER = "offer_button"
    CLOSE = "close_button"
    DELETE = "delete_button"


class ModalWindow(Modal):
    def __init__(
        self,
        ctx,
        description,
        description_placeholder,
        button_category,
        title,
        pool,
        ticket_purpose,
    ):
        self.button_category = button_category
        self.pool = pool
        self.description_custom_id = f"desc-{ctx.id}"
        self.ticket_purpose = ticket_purpose
        components = [
            discord.ui.TextInput(
                label=description,
                placeholder=description_placeholder,
                style=discord.TextInputStyle.long,
                custom_id=f"desc-{ctx.id}",
            )
        ]
        super().__init__(
            title=title,
            timeout=200,
            custom_id=f"ticket_window_{ctx.id}",
            components=components,
        )

    async def callback(self, ctx: discord.Interaction):
        await ctx.response.defer(ephemeral=True)

        async def send_initial_message(_channel, roles, ticket_purpose):
            embed = discord.Embed(
                title=ticket_purpose, color=discord.Color.blue()
            ).add_field(
                name="Описание",
                value=ctx.text_values[self.description_custom_id][:1024],
                inline=False,
            )
            query = "SELECT close_button FROM ticket_button_emoji WHERE guild_id = $1"
            emoji = await self.pool.fetchval(query, ctx.guild.id)
            await _channel.send(
                embed=embed,
                components=[
                    discord.ui.Button(
                        label="Закрыть билет",
                        style=discord.ButtonStyle.red,
                        custom_id="close_button",
                        emoji=emoji or "✖",
                    )
                ],
            )
            allowed_mentions = discord.AllowedMentions(users=True, roles=True)
            roles_mention = ", ".join([role.mention for role in roles])
            await _channel.send(
                f"{roles_mention}, {ticket_purpose} от {ctx.author.mention}",
                allowed_mentions=allowed_mentions,
            )

            await ctx.edit_original_response(f"Билет создан: {channel.mention}")

        query = "SELECT category_id FROM ticket WHERE guild_id = $1"
        tickets_category_id = await self.pool.fetchval(query, ctx.guild.id)
        no_settings_found_message = (
            "Не найдены роли для упоминания. Обратитесь к администратору"
        )

        if self.button_category == ButtonsIDs.QUESTION:
            query = "SELECT question_roles_ids FROM ticket_roles WHERE guild_id = $1"
            result = await self.pool.fetchval(query, ctx.guild.id)

            if not result:
                await ctx.respond(no_settings_found_message, ephemeral=True)
                return
            roles_id = list(result)
            roles_to_add = [ctx.guild.get_role(role_id) for role_id in roles_id]
            channel = await self.create_ticket_channel(
                ctx=ctx,
                tickets_category_id=tickets_category_id,
                roles=roles_to_add,
                channel_name="вопрос",
            )
            await send_initial_message(
                _channel=channel, roles=roles_to_add, ticket_purpose="вопрос"
            )

        elif self.button_category == ButtonsIDs.REPORT:
            query = "SELECT report_roles_ids FROM ticket_roles WHERE guild_id = $1"
            roles_id = list(await self.pool.fetchval(query, ctx.guild.id))

            if not roles_id:
                await ctx.respond(no_settings_found_message, ephemeral=True)
                return
            roles_to_add = [ctx.guild.get_role(role_id) for role_id in roles_id]
            channel = await self.create_ticket_channel(
                ctx=ctx,
                tickets_category_id=tickets_category_id,
                roles=roles_to_add,
                channel_name=self.ticket_purpose,
            )
            await send_initial_message(
                _channel=channel, roles=roles_to_add, ticket_purpose=self.ticket_purpose
            )

        elif self.button_category == ButtonsIDs.OFFER:
            query = "SELECT offer_roles_ids FROM ticket_roles WHERE guild_id = $1"
            roles_id = list(await self.pool.fetchval(query, ctx.guild.id))

            if not roles_id:
                await ctx.respond(no_settings_found_message, ephemeral=True)
                return
            roles_to_add = [ctx.guild.get_role(role_id) for role_id in roles_id]
            channel = await self.create_ticket_channel(
                ctx=ctx,
                tickets_category_id=tickets_category_id,
                roles=roles_to_add,
                channel_name=self.ticket_purpose,
            )
            await send_initial_message(
                _channel=channel, roles=roles_to_add, ticket_purpose=self.ticket_purpose
            )

        ticket_number = await get_ticket_number(self.pool, ctx)

        await send_ticket_log(
            pool=self.pool,
            ctx=ctx,
            title=f"Билет #{ticket_number} создан",
            description=f"Создан участником {
                ctx.author.mention}(`{ctx.author.id}`)\n"
            f"**Категория**\n"
            f"{self.ticket_purpose}\n"
            f"**Описание**\n"
            f"{ctx.text_values[self.description_custom_id][:1024]}\n",
            color=discord.Color.green(),
        )

    async def create_ticket_channel(
        self, ctx, tickets_category_id, roles: list, channel_name
    ):
        guild = ctx.guild
        bot = ctx.message.author
        member = ctx.author
        category = ctx.guild.get_channel(tickets_category_id)
        ticket_overwrite = discord.PermissionOverwrite(
            send_messages=True, view_channel=True
        )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            bot: ticket_overwrite,
            member: ticket_overwrite,
        }

        for role in roles:
            overwrites[role] = ticket_overwrite

        query = "UPDATE ticket SET number = number + 1 WHERE guild_id = $1"
        await self.pool.execute(query, ctx.guild.id)

        ticket_number = await get_ticket_number(self.pool, ctx)
        try:
            channel = await guild.create_text_channel(
                name=f"{ticket_number}┃{member}-{channel_name}",
                category=category,
                overwrites=overwrites,
                topic=f"Билет #{ticket_number}",
            )
            return channel
        except discord.errors.Forbidden:
            await ctx.respond(
                "Не удалось создать канал билета: недостаточно прав. Обратитесь к администратору",
                ephemeral=True,
            )


class TicketsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = asyncpg.Pool = bot.get_pool()

    create = SlashCommandGroup("create", "Создать сообщение с кнопками для билетов")
    start = create.create_subgroup("start")

    @start.command()
    async def tickets_creator(
        self, ctx: discord.ApplicationContext, image_url: str = None
    ):
        """Создать embed с кнопками
        Parameters
        ----------
        ctx: command interaction
        image_url: Добавить изображение
        """
        query = "SELECT question_button FROM ticket_button_emoji WHERE guild_id = $1"
        question_button_emoji = await self.pool.fetchval(query, ctx.guild.id)

        query = "SELECT report_button FROM ticket_button_emoji WHERE guild_id = $1"
        report_button_emoji = await self.pool.fetchval(query, ctx.guild.id)

        query = "SELECT offer_button FROM ticket_button_emoji WHERE guild_id = $1"
        offer_button_emoji = await self.pool.fetchval(query, ctx.guild.id)

        button_question = Button(
            label="Вопрос",
            style=discord.ButtonStyle.grey,
            custom_id="question_button",
            emoji=question_button_emoji or "❔",
        )
        button_report = discord.ui.Button(
            label="Жалоба",
            style=discord.ButtonStyle.red,
            custom_id="report_button",
            emoji=report_button_emoji or "❕",
        )
        button_offer = discord.ui.Button(
            label="Предложение",
            style=discord.ButtonStyle.blurple,
            custom_id="offer_button",
            emoji=offer_button_emoji or "📝",
        )
        view = View()
        view.add_item(button_question)
        view.add_item(button_report)
        view.add_item(button_offer)
        embeds = []
        if image_url:
            embed1 = discord.Embed(description="", color=0x3F8FDF).set_image(
                url=image_url
            )
            embeds.append(embed1)

        embed2 = discord.Embed(
            description="Воспользовавшись кнопками ниже можно написать модераторам по интересующим темам:",
            color=0x3F8FDF,
        ).set_image(
            url="https://media.discordapp.net/attachments/1015290335779364958/1015295923829608468/unknown.png"
        )
        embeds.append(embed2)
        await ctx.send(embeds=embeds, view=view)
        await ctx.respond("Создан embed с кнопками", ephemeral=True)
        # try:
        # except:
        #     await ctx.respond("Не удалось отправить сообщение.\n"
        #                    "Убедитесь, что я могу:\n"
        #                    "Просматривать канал\n"
        #                    "Отправлять сообщения\n"
        #                    "Встраивать ссылки\n",
        #                    ephemeral=True
        #                    )
        #

    async def is_ticket(self, ctx):
        query = "SELECT category_id FROM ticket WHERE guild_id = $1"
        category_id = await self.pool.fetchval(query, ctx.guild.id)

        if ctx.channel.category.id == category_id:
            return True
        else:
            return False

    user = SlashCommandGroup("user", "Добавить или удалить участника в билете")

    @user.command()
    async def add(self, ctx: discord.ApplicationContext, member: discord.Member):
        """Добавить участника в этот канал"""
        if not await self.is_ticket(ctx):
            await ctx.respond(
                "Вы можете использовать эту команду только в билетах", ephemeral=True
            )
            return
        overwrite = discord.PermissionOverwrite(view_channel=True)
        await ctx.channel.set_permissions(member, overwrite=overwrite)
        await ctx.respond(f"Пользователь {member.mention} добавлен в этот чат")

    @user.command()
    async def remove(self, ctx: discord.ApplicationContext, member: discord.Member):
        """Убрать участника из этого канала"""
        if not await self.is_ticket(ctx):
            await ctx.respond(
                "Вы можете использовать эту команду только в билетах", ephemeral=True
            )
            return
        await ctx.channel.set_permissions(member, overwrite=None)
        await ctx.respond(f"Пользователь {member.mention} удалён из этого чата")


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = bot.get_pool()

    @commands.Cog.listener()
    async def on_button_click(self, ctx: discord.MessageInteraction):
        print("Button clicked")
        button_id = ctx.component.custom_id
        guild_id = ctx.guild.id

        if button_id not in ButtonsIDs:
            return

        if button_id == ButtonsIDs.CLOSE:
            await ctx.response.defer()
            channel: discord.TextChannel = ctx.channel  # type: ignore
            channel_overwrites = channel.overwrites
            for key in channel_overwrites:
                if str(key) == "@everyone":
                    continue
                if key == self.bot.user:
                    continue
                if isinstance(key, discord.Member):
                    await channel.set_permissions(
                        key, view_channel=False, send_messages=False
                    )
                    continue
                await channel.set_permissions(
                    key, view_channel=True, send_messages=False
                )

            query = "SELECT closed_ticket_category_id FROM ticket WHERE guild_id = $1"
            closed_tickets_category_id = await self.pool.fetchval(query, guild_id)
            if closed_tickets_category_id:
                category = ctx.guild.get_channel(closed_tickets_category_id)
                await channel.move(category=category, beginning=True)

            embed = discord.Embed(
                description=f"Билет закрыт пользователем {ctx.author.name}.\n"
                f"Нажмите на кнопку для удаления канала"
            )

            query = "SELECT delete_button FROM ticket_button_emoji WHERE guild_id = $1"
            emoji = await self.pool.fetchval(query, ctx.guild.id)

            await channel.send(
                embed=embed,
                components=[
                    discord.ui.Button(
                        label="Удалить билет",
                        style=discord.ButtonStyle.red,
                        custom_id="delete_button",
                        emoji=emoji or "✖",
                    )
                ],
            )
            await ctx.message.edit(components=None)
            ticket_number = ctx.channel.topic.split("#")[1]
            await send_ticket_log(
                pool=self.pool,
                title=f"Билет #{ticket_number} закрыт",
                ctx=ctx,
                description=f"Закрыт участником {ctx.author.mention}(`{
                    ctx.author.id
                }`)",
                color=discord.Color.yellow(),
            )

        if button_id == ButtonsIDs.DELETE:
            await ctx.response.defer()
            ticket_number = ctx.channel.topic.split("#")[1]
            await send_ticket_log(
                pool=self.pool,
                title=f"Билет #{ticket_number} удалён",
                ctx=ctx,
                description=f"Удалён участником {ctx.author.mention}(`{ctx.author.id}`)",
                color=discord.Color.red(),
            )

            await ctx.channel.delete()

        # try:
        #     query = "SELECT button_cooldown_end_time " \
        #             "FROM ticket_users_button_cooldown " \
        #             "WHERE guild_id = $1 and user_id = $2"
        #     user_button_cooldown = await self.pool.fetchval(query, guild_id,
        #                                                     ctx.user.id)
        #     user_button_cooldown = timedelta(minutes=user_button_cooldown)
        #
        # except:
        #     await ctx.respond(
        #         "Настройки для сервера не найдены. Обратитесь к администратору", ephemeral=True)
        #     return

        if button_id == ButtonsIDs.QUESTION:
            modal_window = ModalWindow(
                description="Полный вопрос",
                description_placeholder="Напишите свой вопрос развёрнуто",
                ctx=ctx,
                button_category=ButtonsIDs.QUESTION,
                title="Задать вопрос",
                pool=self.pool,
                ticket_purpose="Вопрос",
            )
            await ctx.response.send_modal(modal_window)

        elif button_id == ButtonsIDs.REPORT:
            modal_window = ModalWindow(
                description="Полная информация",
                description_placeholder="Опишите ситуацию полностью",
                ctx=ctx,
                button_category=ButtonsIDs.REPORT,
                title="Подать жалобу",
                pool=self.pool,
                ticket_purpose="Жалоба",
            )
            await ctx.response.send_modal(modal_window)

        elif button_id == ButtonsIDs.OFFER:
            modal_window = ModalWindow(
                description="Полное предложение",
                description_placeholder="Напишите своё предложение развёрнуто",
                ctx=ctx,
                button_category=ButtonsIDs.OFFER,
                title="Предложить идею",
                pool=self.pool,
                ticket_purpose="Предложение",
            )
            await ctx.response.send_modal(modal_window)


def setup(bot):
    bot.add_cog(TicketsCommands(bot))
    bot.add_cog(Tickets(bot))
