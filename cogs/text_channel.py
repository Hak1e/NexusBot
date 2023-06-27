import disnake
from disnake.ext import commands
import os
from dotenv import load_dotenv
import json

load_dotenv()

MAX_VIEWS_IN_MENU = 25
MAX_BUTTONS_COUNT = 5

########################### Пока не работает корректно ###############################
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





    @commands.slash_command()
    async def setup(
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


        # # Button press
        #
        #
        # await ctx.send("Укажите ID категории:")
        # category_id = await self.bot.wait_for("message", check=check)
        # category = None
        #
        # while not category:
        #     try:
        #         category_id = int(category_id.content)
        #         category = self.bot.get_channel(category_id)
        #         if not isinstance(category, disnake.CategoryChannel):
        #             raise ValueError
        #     except (ValueError, AttributeError):
        #         await ctx.send("Категория не найдена, попробуйте ещё раз:")
        #         category_id = await self.bot.wait_for("message", check=check)




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


def setup(bot):
    bot.add_cog(TextChannel(bot))
