import disnake
from disnake.ext import commands
import asyncio
import asyncpg
import logging
from constants import MAX_ITEMS_IN_MENU, MAX_SELECT_MENUS
import enum
from models.lobby_settings import AuthorSettings, RequestedRole, LobbyChannelSettings


def generate_initial_embed_message(member):
    return disnake.Embed(title="Добро пожаловать в комнату", color=disnake.Color.blurple(),
                         description=f"Владелец: {member.mention}\n"
                                     "Используйте кнопки ниже для настройки канала.\n"
                                     "Если кнопки перестали работать, воспользуйтесь "
                                     "слеш-командой `/channel dashboard` для повторного вызова "
                                     "сообщения с кнопками или используйте другие слеш-команды "
                                     "для комнаты без взаимодействия с кнопками")


class ChannelActions(str, enum.Enum):
    kick = "kick"
    ban = "ban"
    unban = "unban"
    edit_name = "edit_name"
    edit_bitrate = "edit_bitrate"
    edit_user_limit = "edit_user_limit"


class LobbyInfoChannel(str, enum.Enum):
    not_found = "not_found"
    not_needed = "not_needed"


class MembersSelectMenu(disnake.ui.Select):
    def __init__(self, members,
                 pool, bot,
                 action=ChannelActions.kick):
        options = [disnake.SelectOption(label=member.name, value=str(member.id)) for member in members]
        super().__init__(
            placeholder="Выберите участников",
            min_values=1,
            max_values=len(options),
            options=options
        )
        self.action = action
        self.pool = pool
        self.author_settings = AuthorSettings(bot)

    async def callback(self, ctx: disnake.MessageInteraction):
        await ctx.response.defer()
        selected_members_ids = self.values
        voice_channel: disnake.VoiceChannel = ctx.author.voice.channel
        if self.action == ChannelActions.unban:
            for member_id in selected_members_ids:
                member = ctx.guild.get_member(int(member_id))
                await voice_channel.set_permissions(member, overwrite=None)
        else:
            for member_id in selected_members_ids:
                member = ctx.guild.get_member(int(member_id))
                if self.action == ChannelActions.ban:
                    await voice_channel.set_permissions(member, connect=False)
                if member in ctx.channel.members:
                    await member.move_to(None)  # type: ignore
        if not self.action == ChannelActions.kick:
            await self.update_voice_channel_overwrites(voice_channel)


class BaseDashboardButtons(disnake.ui.View):
    def __init__(self, pool,
                 bot):
        self.bot = bot
        self.pool = pool
        self.lobby_settings = LobbyChannelSettings(bot)
        super().__init__(timeout=300)
        self.author_settings = AuthorSettings(bot)

    async def on_timeout(self) -> None:
        self.stop()

    async def create_member_select_menus(self, ctx,
                                         members, action=ChannelActions.kick):
        menus = []
        for position in range(0, len(members), MAX_ITEMS_IN_MENU):
            menu = MembersSelectMenu(members[position:position + MAX_ITEMS_IN_MENU], action=action,
                                     pool=self.pool, bot=self.bot)
            menus.append(menu)

        view = disnake.ui.View()
        menu_number = 0
        part = 1
        for counter in range(len(menus) + 1):
            if menu_number == MAX_SELECT_MENUS:
                await ctx.send(view=view,
                               ephemeral=True)
                menu_number = 0
                part += 1
            elif counter == len(menus):
                await ctx.send(view=view,
                               ephemeral=True)
            else:
                view.add_item(menus[counter])
                menu_number += 1

    async def is_channel_author(self, ctx):
        if await self.author_settings.get_voice_channel_author_id(ctx.channel) != ctx.author.id:
            return False
        return True

    @disnake.ui.button(label="Выгнать", style=disnake.ButtonStyle.blurple)
    async def kick_from_room(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if not await self.is_channel_author(ctx):
            await ctx.send("Вы можете использовать кнопки только в своём канале", ephemeral=True)
            return
        members = [member for member in ctx.channel.members if member != ctx.author]
        if not members:
            await ctx.send("В канале никого, кроме Вас", ephemeral=True)
            return
        await self.create_member_select_menus(ctx, members)

    @disnake.ui.button(label="Забанить", style=disnake.ButtonStyle.blurple)
    async def ban_in_room(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if not await self.is_channel_author(ctx):
            await ctx.send("Вы можете использовать кнопки только в своём канале", ephemeral=True)
            return
        members = [member for member in ctx.channel.members if member != ctx.author]
        if not members:
            await ctx.send("В канале никого, кроме Вас", ephemeral=True)
            return
        await self.create_member_select_menus(ctx, members,
                                              ChannelActions.ban)

    @disnake.ui.button(label="Разбанить", style=disnake.ButtonStyle.blurple)
    async def unban_in_room(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if not await self.is_channel_author(ctx):
            await ctx.send("Вы можете использовать кнопки только в своём канале", ephemeral=True)
            return
        channel: disnake.VoiceChannel = ctx.channel  # type: ignore
        members = []
        for value, permission in channel.overwrites.items():
            if permission.connect is False:
                members.append(value)
        if not members:
            await ctx.send("В настройках канала нет заблокированных участников", ephemeral=True)
            return
        await self.create_member_select_menus(ctx, members,
                                              ChannelActions.unban)

    @disnake.ui.button(label="Лимит", style=disnake.ButtonStyle.blurple)
    async def change_room_limit(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if not await self.is_channel_author(ctx):
            await ctx.send("Вы можете использовать кнопки только в своём канале", ephemeral=True)
            return
        modal_window = ModalWindow(ctx, self.pool,
                                   "0 - 99", "Введите лимит участников",
                                   ChannelActions.edit_user_limit, self.bot)
        await ctx.response.send_modal(modal_window)
        assert isinstance(ctx.channel, disnake.VoiceChannel)
        message = await self.lobby_settings.get_lobby_info_message(ctx.channel)
        if message:
            await self.lobby_settings.update_lobby_info_message(message, ctx.channel)


class ModalWindow(disnake.ui.Modal):
    def __init__(self, ctx,
                 pool, placeholder_text,
                 text_input_title, action,
                 bot):
        self.pool = pool
        self.action = action
        self.author_settings = AuthorSettings(bot)
        self.lobby_settings = LobbyChannelSettings(bot)
        text_input = disnake.ui.TextInput(label="Новое значение", style=disnake.TextInputStyle.short,
                                          max_length=50, custom_id=f"text_input-{ctx.id}",
                                          placeholder=placeholder_text)
        super().__init__(title=text_input_title, custom_id=f"modal-{ctx.id}",
                         components=text_input)

    async def callback(self, ctx: disnake.ModalInteraction):
        voice_channel = ctx.channel
        key, value = list(ctx.text_values.items())[0]
        value = value[:1024]
        if self.action == ChannelActions.edit_name:
            await voice_channel.edit(name=value)
            await ctx.send(embed=disnake.Embed(description=f"Название канала успешно изменено на: {value}",
                                               color=disnake.Color.green()), ephemeral=True)
            await self.author_settings.update_voice_channel_name(ctx.channel)
        elif self.action == ChannelActions.edit_bitrate:
            try:
                await voice_channel.edit(bitrate=int(value) * 1000)
                await ctx.send(embed=disnake.Embed(description=f"Битрейт канала успешно изменен на: `{value}`",
                                                   color=disnake.Color.green()), ephemeral=True)
                await self.author_settings.update_voice_channel_bitrate(ctx.channel)
            except disnake.errors.HTTPException:
                await ctx.send(embed=disnake.Embed(description="Введено неверное значение битрейта",
                                                   color=disnake.Color.red()), ephemeral=True)
        elif self.action == ChannelActions.edit_user_limit:
            if 0 <= int(value) <= 99:
                await voice_channel.edit(user_limit=value)
                await ctx.send(embed=disnake.Embed(description=f"Лимит пользователей успешно изменен на: `{value}`",
                                                   color=disnake.Color.green()), ephemeral=True)
                custom_room = await self.lobby_settings.is_custom(ctx.channel.id)
                if custom_room:
                    await self.author_settings.update_voice_channel_limit(ctx.channel)
            else:
                await ctx.send(embed=disnake.Embed(description="Введено неверное значение лимита пользователей.\n"
                                                               "Введите число от 0 до 99 включительно",
                                                   color=disnake.Color.red()), ephemeral=True)


class CustomChannelDashboardButtons(BaseDashboardButtons):
    @disnake.ui.button(label="Скрыть/Открыть", style=disnake.ButtonStyle.blurple)
    async def change_room_visibility(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if not await self.is_channel_author(ctx):
            await ctx.send("Вы можете использовать кнопки только в своём канале", ephemeral=True)
            return
        default_role = ctx.guild.default_role
        current_view_channel_permission = ctx.channel.permissions_for(default_role).view_channel
        await ctx.channel.set_permissions(default_role, view_channel=not current_view_channel_permission)
        await ctx.send("Комната скрыта" if current_view_channel_permission is not False else "Комната больше не скрыта",
                       ephemeral=True)
        assert isinstance(ctx.channel, disnake.VoiceChannel)
        await self.author_settings.update_voice_channel_overwrites(ctx.channel)

    @disnake.ui.button(label="Закрыть/открыть", style=disnake.ButtonStyle.blurple)
    async def change_room_access(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if not await self.is_channel_author(ctx):
            await ctx.send("Вы можете использовать кнопки только в своём канале", ephemeral=True)
            return
        default_role = ctx.guild.default_role
        current_connect_permission = ctx.channel.permissions_for(default_role).connect
        await ctx.channel.set_permissions(default_role, connect=not current_connect_permission)
        assert isinstance(ctx.channel, disnake.VoiceChannel)
        await self.author_settings.update_voice_channel_overwrites(ctx.channel)
        await ctx.send("Комната закрыта" if current_connect_permission is not False else "Комната больше не закрыта",
                       ephemeral=True)

    @disnake.ui.button(label="Название", style=disnake.ButtonStyle.blurple)
    async def change_room_name(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if not await self.is_channel_author(ctx):
            await ctx.send("Вы можете использовать кнопки только в своём канале", ephemeral=True)
            return
        modal_window = ModalWindow(ctx, self.pool,
                                   "Название канала", "Введите новое название канала",
                                   ChannelActions.edit_name, self.bot)
        await ctx.response.send_modal(modal_window)
        await self.author_settings.update_voice_channel_name(ctx.channel)

    @disnake.ui.button(label="Битрейт", style=disnake.ButtonStyle.blurple)
    async def change_room_bitrate(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if not await self.is_channel_author(ctx):
            await ctx.send("Вы можете использовать кнопки только в своём канале", ephemeral=True)
            return
        modal_window = ModalWindow(ctx, self.pool,
                                   f"8 - {int(ctx.guild.bitrate_limit / 1000)}", "Введите битрейт канала",
                                   ChannelActions.edit_bitrate, self.bot)
        await ctx.response.send_modal(modal_window)
        assert isinstance(ctx.channel, disnake.VoiceChannel)
        await self.author_settings.update_voice_channel_bitrate(ctx.channel)


class Lobby(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = self.bot.get_pool()
        self.lobby_settings = LobbyChannelSettings(bot)

    @staticmethod
    def create_lobby_info_embed(member, role: disnake.Role,
                                voice_channel: disnake.VoiceChannel, user_limit):
        if user_limit == 0 or not user_limit:
            user_limit = "∞"
        try:
            color = role.color
        except AttributeError:
            color = 0x3f8fdf
        try:
            role_icon_url = role.icon.url
        except AttributeError:
            role_icon_url = None

        embed = (
            disnake.Embed(title="**Участники:**", color=color)
            .add_field("", f"【1】{member.mention}\n")
            .add_field("", f"\n**✅ Канал:** {voice_channel.mention}",
                       inline=False)
            .set_thumbnail(role_icon_url)
            .set_footer(text=f"Участников: 1/{user_limit}")
        )
        return embed

    async def create_voice_channel(self, member,
                                   category, overwrites,
                                   voice_creator,
                                   user_limit=None, required_role=None,
                                   custom=False, custom_channel_name=None,
                                   bitrate=None):
        if custom:
            channel_name = custom_channel_name or f"{member.name}'s channel"
            voice_channel = await member.guild.create_voice_channel(name=channel_name, category=category,
                                                                    overwrites=overwrites, bitrate=bitrate,
                                                                    user_limit=user_limit)
            return voice_channel
        else:
            if isinstance(required_role, disnake.Role):
                query = ("SELECT channel_with_role_prefix "
                         "FROM lobby_voice_channel_creator_settings "
                         "WHERE id = $1")
                prefix = await self.pool.fetchval(query, voice_creator.id)
                if prefix:
                    voice_channel_name = f"{prefix}{required_role.name}"
                else:
                    voice_channel_name = f"【🏆】{required_role.name}"
            else:
                query = ("SELECT default_name "
                         "FROM lobby_voice_channel_creator_settings "
                         "WHERE id = $1")
                default_channel_name = await self.pool.fetchval(query, voice_creator.id)
                query = ("SELECT channel_without_role_prefix "
                         "FROM lobby_voice_channel_creator_settings "
                         "WHERE id = $1")
                prefix = await self.pool.fetchval(query, voice_creator.id)
                voice_channel_name = ""
                if prefix:
                    voice_channel_name += prefix
                if default_channel_name:
                    voice_channel_name += default_channel_name
                else:
                    voice_channel_name += f"【🎮】{category.name}"

            voice_channel = await member.guild.create_voice_channel(name=voice_channel_name, category=category,
                                                                    overwrites=overwrites, user_limit=user_limit)
            return voice_channel

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member,
                                    before: disnake.VoiceState, current: disnake.VoiceState):
        if before.channel == current.channel:
            return

        guild_id = member.guild.id
        temp_overwrites = {member.guild.default_role: disnake.PermissionOverwrite(view_channel=False),
                           self.bot.user: disnake.PermissionOverwrite(view_channel=True)}

        if before.channel:
            print(f"Before channel {before.channel.name}")
            voice_creator_id = await self.lobby_settings.get_channel_creator_id(before.channel.id)
            if not voice_creator_id:
                return
            print("Left lobby room")
            if not before.channel.members:
                await before.channel.edit(overwrites=temp_overwrites)
                print("Before channel is empty. Deleting")
                message = await self.lobby_settings.get_lobby_info_message(before.channel)
                if message:
                    await self.lobby_settings.delete_message_id_from_db(message.id)
                    await message.delete()
                    print("Lobby info message deleted")
                await self.lobby_settings.delete_voice_channel_author_id(before.channel)
                await self.lobby_settings.delete_created_voice_channel_from_db(before.channel)
                print("[2] Deleting channel")
                try:
                    await before.channel.delete()
                except disnake.errors.NotFound:
                    print(f"Error while deleting channel")
            elif before.channel.members:
                print("Before channel is not empty. Updating lobby info")
                message = await self.lobby_settings.get_lobby_info_message(before.channel)
                if message:
                    await self.lobby_settings.update_lobby_info_message(message, before.channel)

        if current.channel:
            print(f"Current channel {current.channel.name}")
            query = ("SELECT id, custom "
                     "FROM lobby_voice_channel_creator_settings "
                     "WHERE id = $1")
            is_voice_creator = await self.pool.fetchrow(query, current.channel.id)
            if is_voice_creator:
                voice_creator_id, custom = is_voice_creator
                if voice_creator_id:
                    print("Voice creator")
                    query = ("SELECT category_id_for_new_channel "
                             "FROM lobby_voice_channel_creator_settings "
                             "WHERE id = $1")
                    lobby_category_id = await self.pool.fetchval(query, current.channel.id)
                    if not lobby_category_id:
                        logging.error(f"Категория для создания каналов не найдена в базе данных")
                        return
                    category = member.guild.get_channel(lobby_category_id)
                    overwrites = await self.lobby_settings.get_channel_overwrites(category, member)
                    hello_embed = generate_initial_embed_message(member)
                    if custom:
                        channel_name, bitrate, user_limit = await self.lobby_settings.get_custom_channel_settings(
                            guild_id, member)
                        voice_channel = await self.create_voice_channel(member=member, category=category,
                                                                        overwrites=overwrites, custom=True,
                                                                        custom_channel_name=channel_name,
                                                                        bitrate=bitrate, user_limit=user_limit,
                                                                        voice_creator=current.channel)
                        print("Custom channel created. Trying to move member")
                        try:
                            await member.move_to(voice_channel)
                            print(f"Moved {member.name} to {voice_channel.name}")
                        except disnake.errors.HTTPException:
                            print("[1] Deleting channel")
                            await voice_channel.delete()
                            return
                        await asyncio.sleep(1)
                        if voice_channel.members:
                            await self.lobby_settings.add_lobby_channel_to_db(voice_channel.id, voice_creator_id)
                            await self.lobby_settings.set_voice_channel_author_id(member, voice_channel)
                            buttons = CustomChannelDashboardButtons(self.pool, self.bot)
                            await voice_channel.send(embed=hello_embed, view=buttons)
                    else:
                        required_role = await self.lobby_settings.get_channel_required_role(member, current.channel.id)
                        query = ("SELECT user_limit "
                                 "FROM lobby_voice_channel_creator_settings "
                                 "WHERE id = $1")
                        user_limit = await self.pool.fetchval(query, voice_creator_id)
                        voice_channel = await self.create_voice_channel(member=member, category=category,
                                                                        overwrites=temp_overwrites,
                                                                        user_limit=user_limit,
                                                                        required_role=required_role,
                                                                        voice_creator=current.channel)
                        print("Channel created. Trying to move member")
                        try:
                            await member.move_to(voice_channel)
                            print(f"Moved {member.name} to {voice_channel.name}")
                        except disnake.errors.HTTPException:
                            print("[1] Deleting channel")
                            await voice_channel.delete()
                            return
                        await asyncio.sleep(1)
                        if voice_channel.members:
                            await self.lobby_settings.add_lobby_channel_to_db(voice_channel.id, voice_creator_id)
                            await self.lobby_settings.set_voice_channel_author_id(member, voice_channel)
                            if required_role == RequestedRole.missing:
                                query = ("SELECT role_not_found_message "
                                         "FROM lobby_voice_channel_creator_settings "
                                         "WHERE id = $1")
                                role_not_found_message = await self.pool.fetchval(query, voice_creator_id)
                                default_error_message = (
                                    f"У Вас не была найдена подходящая роль для данной категории.\n"
                                    f"Пожалуйста, выберите подходящую роль в разделе <id:customize> или в канале с "
                                    f"выбором ролей")
                                error_message = role_not_found_message or default_error_message
                                embed = disnake.Embed(description=error_message, color=disnake.Color.red())
                                if not role_not_found_message:
                                    await voice_channel.send(f"{member.mention},", embed=embed)
                                else:
                                    await voice_channel.send(embed=embed)
                            embed = self.create_lobby_info_embed(member, required_role,
                                                                 voice_channel, voice_channel.user_limit)

                            lobby_log_needed = await self.lobby_settings.log_needed(voice_creator_id)
                            if lobby_log_needed:
                                print("Log needed")
                                text_channel_id = await self.lobby_settings.get_text_channel_id(voice_creator_id)
                                text_channel = member.guild.get_channel(text_channel_id)
                                await voice_channel.edit(overwrites=overwrites)
                                if not text_channel:
                                    await voice_channel.send(f"{member.mention}, "
                                                             f"Оповещение о создании комнаты не было создано из-за неверных"
                                                             f" настроек. Обратитесь к администратору за помощью")
                                elif text_channel:
                                    lobby_info_message = await text_channel.send(embed=embed)
                                    await self.lobby_settings.save_message_id_to_db(voice_channel, lobby_info_message)
                            buttons = BaseDashboardButtons(self.pool, self.bot)
                            await voice_channel.send(embed=hello_embed, view=buttons)
                    if voice_channel and not voice_channel.members:
                        print("[3] Пользователя нет в голосовом канале. Канал будет удалён")
                        try:
                            await voice_channel.delete()
                        except disnake.errors.NotFound:
                            return

            else:
                voice_creator_id = await self.lobby_settings.get_channel_creator_id(current.channel.id)
                if not voice_creator_id:
                    return
                print("Joined lobby room")
                message = await self.lobby_settings.get_lobby_info_message(current.channel)
                if message:
                    await self.lobby_settings.update_lobby_info_message(message, current.channel)


def setup(bot):
    bot.add_cog(Lobby(bot))
