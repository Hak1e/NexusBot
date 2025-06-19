import discord
from discord.ext import commands
import asyncio
import asyncpg
import logging
from constants import MAX_ITEMS_IN_MENU, MAX_SELECT_MENUS
import enum
from models.lobby_settings import AuthorSettings, RequestedRole, LobbyChannelSettings

MAX_WAIT_TIME = 20


def generate_initial_embed_message(member):
    return discord.Embed(title="Добро пожаловать в комнату", color=discord.Color.blurple(),
                         description=f"Владелец: {member.mention}\n"
                                     "Используйте кнопки ниже для настройки канала.\n\n"
                                     "## ‼️Если кнопки перестали работать ‼️\n"
                                     "Воспользуйтесь слеш-командой `/channel dashboard` для повторного вызова "
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


class MembersSelectMenu(discord.ui.Select):
    def __init__(self, members,
                 pool, bot,
                 action=ChannelActions.kick):
        options = [discord.SelectOption(label=member.name, value=str(member.id)) for member in members]
        super().__init__(
            placeholder="Выберите участников",
            min_values=1,
            max_values=len(options),
            options=options
        )
        self.action = action
        self.pool = pool
        self.author_settings = AuthorSettings(bot)

    async def callback(self, ctx: discord.MessageInteraction):
        await ctx.response.defer()
        selected_members_or_roles_ids = self.values
        voice_channel: discord.VoiceChannel = ctx.author.voice.channel
        if self.action == ChannelActions.unban:
            for _id in selected_members_or_roles_ids:
                member_or_role = ctx.guild.get_member(int(_id)) or ctx.guild.get_role(int(_id))
                await voice_channel.set_permissions(member_or_role, overwrite=None)
        else:
            for _id in selected_members_or_roles_ids:
                member_or_role = ctx.guild.get_member(int(_id)) or ctx.guild.get_role(int(_id))
                if self.action == ChannelActions.ban:
                    await voice_channel.set_permissions(member_or_role, connect=False)
                if member_or_role in ctx.channel.members:
                    await member_or_role.move_to(None)  # type: ignore
        if not self.action == ChannelActions.kick:
            await self.author_settings.update_voice_channel_overwrites(voice_channel)


class BaseDashboardButtons(discord.ui.View):
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

        view = discord.ui.View()
        menu_number = 0
        part = 1
        for counter in range(len(menus) + 1):
            if menu_number == MAX_SELECT_MENUS:
                await ctx.respond(view=view,
                               ephemeral=True)
                menu_number = 0
                part += 1
            elif counter == len(menus):
                await ctx.respond(view=view,
                               ephemeral=True)
            else:
                view.add_item(menus[counter])
                menu_number += 1

    async def is_channel_author(self, ctx):
        if await self.author_settings.get_voice_channel_author_id(ctx.channel) != ctx.author.id:
            return False
        return True

    @discord.ui.button(label="Выгнать", style=discord.ButtonStyle.blurple)
    async def kick_from_room(self, button: discord.ui.Button, ctx: discord.MessageInteraction):
        if not await self.is_channel_author(ctx):
            await ctx.respond("Вы можете использовать кнопки только в своём канале", ephemeral=True)
            return
        members = [member for member in ctx.channel.members if member != ctx.author]
        if not members:
            await ctx.respond("В канале никого, кроме Вас", ephemeral=True)
            return
        await self.create_member_select_menus(ctx, members)

    @discord.ui.button(label="Забанить", style=discord.ButtonStyle.blurple)
    async def ban_in_room(self, button: discord.ui.Button, ctx: discord.MessageInteraction):
        if not await self.is_channel_author(ctx):
            await ctx.respond("Вы можете использовать кнопки только в своём канале", ephemeral=True)
            return

        members = [member for member in ctx.channel.members if member != ctx.author]
        if not members:
            await ctx.respond("В канале никого, кроме Вас", ephemeral=True)
            return
        await self.create_member_select_menus(ctx, members,
                                              ChannelActions.ban)

    @discord.ui.button(label="Разбанить", style=discord.ButtonStyle.blurple)
    async def unban_in_room(self, button: discord.ui.Button, ctx: discord.MessageInteraction):
        if not await self.is_channel_author(ctx):
            await ctx.respond("Вы можете использовать кнопки только в своём канале", ephemeral=True)
            return
        channel: discord.VoiceChannel = ctx.channel  # type: ignore
        members = []

        query = ("SELECT id "
                 "FROM guild_mute_role "
                 "WHERE guild_id = $1")
        muted_role_id = await self.pool.fetchval(query, ctx.guild.id)

        for value, permission in channel.overwrites.items():
            if value.id == muted_role_id:
                continue
            if permission.connect is False:
                members.append(value)
        if not members:
            await ctx.respond("В настройках канала нет заблокированных участников", ephemeral=True)
            return
        await self.create_member_select_menus(ctx, members,
                                              ChannelActions.unban)

    @discord.ui.button(label="Лимит", style=discord.ButtonStyle.blurple)
    async def change_room_limit(self, button: discord.ui.Button, ctx: discord.MessageInteraction):
        if not await self.is_channel_author(ctx):
            await ctx.respond("Вы можете использовать кнопки только в своём канале", ephemeral=True)
            return
        modal_window = ModalWindow(ctx, self.pool,
                                   "0 - 99", "Введите лимит участников",
                                   ChannelActions.edit_user_limit, self.bot)
        await ctx.response.send_modal(modal_window)
        assert isinstance(ctx.channel, discord.VoiceChannel)


class ModalWindow(discord.ui.Modal):
    def __init__(self, ctx,
                 pool, placeholder_text,
                 text_input_title, action,
                 bot):
        self.pool = pool
        self.action = action
        self.author_settings = AuthorSettings(bot)
        self.lobby_settings = LobbyChannelSettings(bot)
        text_input = discord.ui.TextInput(label="Новое значение", style=discord.TextInputStyle.short,
                                          max_length=50, custom_id=f"text_input-{ctx.id}",
                                          placeholder=placeholder_text)
        super().__init__(title=text_input_title, custom_id=f"modal-{ctx.id}",
                         components=text_input)

    async def callback(self, ctx: discord.Interaction):
        voice_channel = ctx.channel
        key, value = list(ctx.text_values.items())[0]
        value = value[:1024]
        if self.action == ChannelActions.edit_name:
            await voice_channel.edit(name=value)
            await ctx.respond(embed=discord.Embed(description=f"Название канала успешно изменено на: {value}",
                                               color=discord.Color.green()), ephemeral=True)
            await self.author_settings.update_voice_channel_name(ctx.channel)
        elif self.action == ChannelActions.edit_bitrate:
            try:
                await voice_channel.edit(bitrate=int(value) * 1000)
                await ctx.respond(embed=discord.Embed(description=f"Битрейт канала успешно изменен на: `{value}`",
                                                   color=discord.Color.green()), ephemeral=True)
                await self.author_settings.update_voice_channel_bitrate(ctx.channel)
            except discord.errors.HTTPException:
                await ctx.respond(embed=discord.Embed(description="Введено неверное значение битрейта",
                                                   color=discord.Color.red()), ephemeral=True)
        elif self.action == ChannelActions.edit_user_limit:
            if 0 <= int(value) <= 99:
                await voice_channel.edit(user_limit=value)
                await ctx.respond(embed=discord.Embed(description=f"Лимит пользователей успешно изменен на: `{value}`",
                                                   color=discord.Color.green()), ephemeral=True)
                message = await self.lobby_settings.get_lobby_info_message(ctx.channel)
                if message:
                    await self.lobby_settings.update_lobby_info_message(message, ctx.channel)
                custom_room = await self.lobby_settings.is_custom(ctx.channel.id)
                if custom_room:
                    await self.author_settings.update_voice_channel_limit(ctx.channel)
            else:
                await ctx.respond(embed=discord.Embed(description="Введено неверное значение лимита пользователей.\n"
                                                               "Введите число от 0 до 99 включительно",
                                                   color=discord.Color.red()), ephemeral=True)


class CustomChannelDashboardButtons(BaseDashboardButtons):
    @discord.ui.button(label="Скрыть/Открыть", style=discord.ButtonStyle.blurple)
    async def change_room_visibility(self, button: discord.ui.Button, ctx: discord.MessageInteraction):
        if not await self.is_channel_author(ctx):
            await ctx.respond("Вы можете использовать кнопки только в своём канале", ephemeral=True)
            return
        default_role = ctx.guild.default_role
        current_view_channel_permission = ctx.channel.permissions_for(default_role).view_channel
        await ctx.channel.set_permissions(default_role, view_channel=not current_view_channel_permission)
        await ctx.respond("Комната скрыта" if current_view_channel_permission is not False else "Комната больше не скрыта",
                       ephemeral=True)
        assert isinstance(ctx.channel, discord.VoiceChannel)
        await self.author_settings.update_voice_channel_overwrites(ctx.channel)

    @discord.ui.button(label="Закрыть/открыть", style=discord.ButtonStyle.blurple)
    async def change_room_access(self, button: discord.ui.Button, ctx: discord.MessageInteraction):
        if not await self.is_channel_author(ctx):
            await ctx.respond("Вы можете использовать кнопки только в своём канале", ephemeral=True)
            return
        default_role = ctx.guild.default_role
        current_connect_permission = ctx.channel.permissions_for(default_role).connect
        await ctx.channel.set_permissions(default_role, connect=not current_connect_permission)
        assert isinstance(ctx.channel, discord.VoiceChannel)
        await self.author_settings.update_voice_channel_overwrites(ctx.channel)
        await ctx.respond("Комната закрыта" if current_connect_permission is not False else "Комната больше не закрыта",
                       ephemeral=True)

    @discord.ui.button(label="Название", style=discord.ButtonStyle.blurple)
    async def change_room_name(self, button: discord.ui.Button, ctx: discord.MessageInteraction):
        if not await self.is_channel_author(ctx):
            await ctx.respond("Вы можете использовать кнопки только в своём канале", ephemeral=True)
            return
        modal_window = ModalWindow(ctx, self.pool,
                                   "Название канала", "Введите новое название канала",
                                   ChannelActions.edit_name, self.bot)
        await ctx.response.send_modal(modal_window)
        await self.author_settings.update_voice_channel_name(ctx.channel)

    @discord.ui.button(label="Битрейт", style=discord.ButtonStyle.blurple)
    async def change_room_bitrate(self, button: discord.ui.Button, ctx: discord.MessageInteraction):
        if not await self.is_channel_author(ctx):
            await ctx.respond("Вы можете использовать кнопки только в своём канале", ephemeral=True)
            return
        modal_window = ModalWindow(ctx, self.pool,
                                   f"8 - {int(ctx.guild.bitrate_limit / 1000)}", "Введите битрейт канала",
                                   ChannelActions.edit_bitrate, self.bot)
        await ctx.response.send_modal(modal_window)
        assert isinstance(ctx.channel, discord.VoiceChannel)
        await self.author_settings.update_voice_channel_bitrate(ctx.channel)


class Lobby(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = self.bot.get_pool()
        self.lobby_settings = LobbyChannelSettings(bot)
        self.cached_messages = {}
        self.queued_message_id = []

    @staticmethod
    def create_lobby_info_embed(member, role: discord.Role,
                                voice_channel: discord.VoiceChannel, user_limit):
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
            discord.Embed(title="**Участники:**", color=color)
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
            if isinstance(required_role, discord.Role):
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
    async def on_voice_state_update(self, member: discord.Member,
                                    before: discord.VoiceState, current: discord.VoiceState):
        if before.channel == current.channel:
            return

        guild_id = member.guild.id
        temp_overwrites = {member.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                           self.bot.user: discord.PermissionOverwrite(view_channel=True)}

        if before.channel:
            logging.info(f"Before channel ({before.channel.name})")
            voice_creator_id = await self.lobby_settings.get_channel_creator_id(before.channel.id)
            if voice_creator_id:
                logging.info(f"{member.name} left lobby room")
                await asyncio.sleep(1)
                if before.channel.id in self.cached_messages:
                    message = self.cached_messages[before.channel.id]
                    logging.info("Found message in cache")
                else:
                    message = await self.lobby_settings.get_lobby_info_message(before.channel)
                    if message:
                        logging.info("Fetched message from database")
                if not before.channel.members:
                    logging.info(f"Before channel ({before.channel.name}) is empty")
                    channel_overwrites = before.channel.overwrites
                    await before.channel.edit(overwrites=temp_overwrites)
                    counter = 1
                    if message:
                        logging.info("Message found")
                        if message.id in self.queued_message_id:
                            logging.info("Message already in queue")
                        if message.id not in self.queued_message_id:
                            self.queued_message_id.append(message.id)
                            logging.info("Message added in queue")
                            while True:
                                if counter > MAX_WAIT_TIME:
                                    try:
                                        await before.channel.edit(overwrites=channel_overwrites)
                                    except discord.NotFound:
                                        pass
                                    break
                                try:
                                    logging.info("Trying to delete message")
                                    await message.delete()
                                    logging.info("Message deleted")
                                    await self.lobby_settings.delete_message_id_from_db(message.id)
                                    logging.info("Lobby info message deleted from database")
                                    self.queued_message_id.remove(message.id)
                                    break
                                except Exception as e:
                                    logging.error(f"[{counter}] Error while deleting message: {e}")
                                    counter += 1
                                    await asyncio.sleep(1)
                    else:
                        logging.info("Message was not found")
                    counter = 0
                    while True:
                        if counter >= MAX_WAIT_TIME / 2 + 1:
                            break
                        try:
                            logging.info(f"Deleting voice channel ({before.channel.name})")
                            await before.channel.delete()
                            logging.info(f"Voice channel ({before.channel.name}) deleted")
                            await self.lobby_settings.delete_voice_channel_author_id(before.channel)
                            logging.info("Deleted voice channel author from database")
                            await self.lobby_settings.delete_created_voice_channel_from_db(before.channel)
                            logging.info("Deleted created voice channel from database")
                            break
                        except Exception as e:
                            logging.error(
                                f"[{counter}] Error while deleting voice channel ({before.channel.name}): {e}")
                            counter += 1
                            await asyncio.sleep(1)

                elif before.channel.members:
                    logging.info(f"Before channel ({before.channel.name}) is not empty. Updating lobby info")
                    if message:
                        await self.lobby_settings.update_lobby_info_message(message, before.channel)
                        logging.info("Lobby info updated")

        if current.channel:
            logging.info(f"Current channel ({current.channel.name})")
            query = ("SELECT id, custom "
                     "FROM lobby_voice_channel_creator_settings "
                     "WHERE id = $1")
            is_voice_creator = await self.pool.fetchrow(query, current.channel.id)
            if is_voice_creator:
                voice_creator_id, custom = is_voice_creator
                if voice_creator_id:
                    logging.info(f"{member.name} joined in voice creator")
                    query = ("SELECT category_id_for_new_channel "
                             "FROM lobby_voice_channel_creator_settings "
                             "WHERE id = $1")
                    lobby_category_id = await self.pool.fetchval(query, current.channel.id)
                    if not lobby_category_id:
                        logging.error(f"Category for new channel was not found in database")
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
                        logging.info("Custom channel created. Trying to move member")
                        try:
                            await member.move_to(voice_channel)
                            logging.info(f"Moved {member.name} to {voice_channel.name}")
                            await self.lobby_settings.add_lobby_channel_to_db(voice_channel.id, voice_creator_id)
                            logging.info("Voice channel added to database")
                            await self.lobby_settings.set_voice_channel_author_id(member, voice_channel)
                            logging.info("Voice channel author id added to database")
                        except discord.errors.HTTPException:
                            logging.error(f"{member.name}  left while moving")
                            await voice_channel.delete()
                            logging.error("Voice channel deleted")
                            return
                        if voice_channel.members:
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
                        logging.info("Voice channel created. Trying to move member")
                        try:
                            await member.move_to(voice_channel)
                            logging.info(f"Moved {member.name} to {voice_channel.name}")
                            await self.lobby_settings.add_lobby_channel_to_db(voice_channel.id, voice_creator_id)
                            logging.info("Voice channel added to database")
                            await self.lobby_settings.set_voice_channel_author_id(member, voice_channel)
                            logging.info("Voice channel author id added to database")
                        except discord.errors.HTTPException:
                            logging.error(f"{member.name}  left while moving")
                            await voice_channel.delete()
                            logging.error(f"Voice channel ({voice_channel.name}) deleted")
                            return
                        # await asyncio.sleep(1)
                        if voice_channel.members:
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
                                embed = discord.Embed(description=error_message, color=discord.Color.red())
                                if not role_not_found_message:
                                    await voice_channel.send(f"{member.mention},", embed=embed)
                                else:
                                    await voice_channel.send(embed=embed)
                            embed = self.create_lobby_info_embed(member, required_role,
                                                                 voice_channel, voice_channel.user_limit)

                            lobby_log_needed = await self.lobby_settings.log_needed(voice_creator_id)
                            if lobby_log_needed:
                                logging.info("Lobby info needed")
                                text_channel_id = await self.lobby_settings.get_text_channel_id(voice_creator_id)
                                text_channel = member.guild.get_channel(text_channel_id)
                                await voice_channel.edit(overwrites=overwrites)
                                if not text_channel:
                                    await voice_channel.send(f"{member.mention}, "
                                                             f"Оповещение о создании комнаты не было создано из-за неверных"
                                                             f" настроек. Обратитесь к администратору за помощью")
                                elif text_channel:
                                    logging.info("Text channel for lobby info found. Sending message")
                                    lobby_info_message = await text_channel.send(embed=embed)
                                    logging.info("Message sent")
                                    self.cached_messages[voice_channel.id] = lobby_info_message
                                    await self.lobby_settings.save_message_id_to_db(voice_channel, lobby_info_message)
                                    logging.info("Sent message cached and saved to database")
                            buttons = BaseDashboardButtons(self.pool, self.bot)
                            await voice_channel.send(embed=hello_embed, view=buttons)

            else:
                voice_creator_id = await self.lobby_settings.get_channel_creator_id(current.channel.id)
                if not voice_creator_id:
                    return
                logging.info(f"{member.name} joined lobby room ({current.channel.name})")
                if current.channel.id in self.cached_messages:
                    message = self.cached_messages[current.channel.id]
                    logging.info("Found message in cache")
                    await self.lobby_settings.update_lobby_info_message(message, current.channel)
                    logging.info("Lobby info updated")
                else:
                    message = await self.lobby_settings.get_lobby_info_message(current.channel)
                    logging.info("Fetching lobby info from database")
                if message:
                    await self.lobby_settings.update_lobby_info_message(message, current.channel)
                    self.cached_messages[current.channel.id] = message
                    logging.info("Message was updated and saved to database")


def setup(bot):
    bot.add_cog(Lobby(bot))
