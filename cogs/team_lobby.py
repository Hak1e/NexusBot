import asyncio
import disnake
from disnake.ext import commands
import asyncpg
from core.bot import Nexus
import logging
from constants import MAX_ITEMS_IN_MENU, MAX_SELECT_MENUS
import enum


logger = logging.getLogger(__name__)


class ChannelActions(str, enum.Enum):
    kick = "kick"
    ban = "ban"
    unban = "unban"


class MembersSelectMenu(disnake.ui.Select):
    def __init__(self, members,
                 action=ChannelActions.kick):
        options = [disnake.SelectOption(label=member.name, value=str(member.id)) for member in members]
        super().__init__(
            placeholder="Выберите участника",
            min_values=1,
            max_values=len(options),
            options=options
        )
        self.action = action

    async def callback(self, ctx: disnake.MessageInteraction):
        await ctx.response.defer()
        selected_members_ids = self.values
        voice_channel: disnake.VoiceChannel = ctx.author.voice.channel
        if self.action == ChannelActions.unban:
            for member_id in selected_members_ids:
                member = ctx.guild.get_member(int(member_id))
                await voice_channel.set_permissions(member, connect=None)
        else:
            for member_id in selected_members_ids:
                member = ctx.guild.get_member(int(member_id))
                if self.action == ChannelActions.ban:
                    await voice_channel.set_permissions(member, connect=False)
                if member in ctx.channel.members:
                    await member.move_to(None)  # type: ignore


class DashboardButtons(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=0)

    async def on_timeout(self) -> None:
        self.stop()

    @disnake.ui.button(label="Выгнать", style=disnake.ButtonStyle.blurple)
    async def kick_from_room(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        voice_channel = ctx.author.voice.channel
        members = [member for member in voice_channel.members if member != ctx.author]
        if not members:
            await ctx.send("В канале никого, кроме Вас", ephemeral=True)
            return

        menus = []
        for position in range(0, len(members), MAX_ITEMS_IN_MENU):
            menu = MembersSelectMenu(members[position:position + MAX_ITEMS_IN_MENU])
            menus.append(menu)

        view = disnake.ui.View()
        menu_number = 0
        part = 1
        for counter in range(len(menus) + 1):
            if menu_number == MAX_SELECT_MENUS:
                await ctx.send(f"Часть {part}) Выберите участников для отключения:", view=view,
                               ephemeral=True)
                menu_number = 0
                part += 1
            elif counter == len(menus):
                await ctx.send("Выберите участников для отключения:", view=view,
                               ephemeral=True)
            else:
                view.add_item(menus[counter])
                menu_number += 1

    @disnake.ui.button(label="Забанить", style=disnake.ButtonStyle.blurple)
    async def ban_in_room(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        voice_channel = ctx.author.voice.channel
        members = [member for member in voice_channel.members if member != ctx.author]
        if not members:
            await ctx.send("В канале никого, кроме Вас", ephemeral=True)
            return

        menus = []
        for position in range(0, len(members), MAX_ITEMS_IN_MENU):
            menu = MembersSelectMenu(members[position:position + MAX_ITEMS_IN_MENU], action=ChannelActions.ban)
            menus.append(menu)

        view = disnake.ui.View()
        menu_number = 0
        part = 1
        for counter in range(len(menus) + 1):
            if menu_number == MAX_SELECT_MENUS:
                await ctx.send(f"Часть {part}) Выберите участников для бана в этом канале:", view=view,
                               ephemeral=True)
                menu_number = 0
                part += 1
            elif counter == len(menus):
                await ctx.send("Выберите участников для бана в этом канале:", view=view,
                               ephemeral=True)
            else:
                view.add_item(menus[counter])
                menu_number += 1

    #
    # @disnake.ui.button(label="Права", style=disnake.ButtonStyle.blurple)
    # async def room_rights(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
    #     pass


class LobbyChannels(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.get_pool()

    # region Lobby info
    @staticmethod
    def create_lobby_info(member, role: disnake.Role,
                          voice_channel: disnake.VoiceChannel, user_limit):
        if user_limit == 0 or not user_limit:
            user_limit = "∞"
        # role_icon = f"<:{role.name}:{role.id}>" if role else "NET"
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

    async def update_lobby_info(self, members,
                                voice_channel: disnake.VoiceChannel):
        query = ("SELECT message_id "
                 "FROM lobby_messages "
                 "WHERE guild_id = $1 and voice_channel_id = $2")
        message_id = await self.pool.fetchval(query, voice_channel.guild.id,
                                              voice_channel.id)

        query = ("SELECT text_channel_id "
                 "FROM lobby_text_channel_ids "
                 "WHERE guild_id = $1 and lobby_category_id = $2")
        text_channel_id = await self.pool.fetchval(query, voice_channel.guild.id,
                                                   voice_channel.category.id)

        if message_id is None or text_channel_id is None:
            return

        text_channel = voice_channel.guild.get_channel(text_channel_id)
        try:
            message: disnake.Message = await text_channel.fetch_message(message_id)
        except disnake.errors.NotFound:
            return
        updated_embed = message.embeds[0]
        member_enumeration = []
        counter = 1
        for member in members:
            # rank_role = await self.get_rank_role(member, voice_channel)
            # role_icon = f"<:{rank_role.name}:{rank_role.id}>" if rank_role else "NIT"  # type: ignore
            member_enumeration.append(f"【{counter}】{member.mention}")
            counter += 1

        member_list = "\n".join(member_enumeration)
        updated_embed.set_field_at(0, name="", value=f"{member_list}\n")
        user_limit = voice_channel.user_limit
        if user_limit == 0:
            user_limit = "∞"
        if len(voice_channel.members) >= voice_channel.user_limit:
            updated_embed.set_field_at(1, name="", value="**❌ Канал заполнен**",
                                       inline=False)
        else:
            updated_embed.set_field_at(1, "", f"\n**✅ Канал:** {voice_channel.mention}",
                                       inline=False)
        updated_embed.set_footer(text=f"Участников: {len(members)}/{user_limit}")
        await message.edit(embed=updated_embed)

    async def send_lobby_info(self, member: disnake.Member,
                              created_voice_channel, embed):

        text_channel_id_query = ("SELECT text_channel_id "
                                 "FROM lobby_text_channel_ids "
                                 "WHERE guild_id = $1 and lobby_category_id = $2")
        text_channel_id = await self.pool.fetchval(text_channel_id_query, member.guild.id,
                                                   created_voice_channel.category.id)
        if not text_channel_id:
            return await created_voice_channel.send(f"{member.mention}, "
                                                    f"Оповещение о создании комнаты не было создано из-за неверных "
                                                    f"настроек. Обратитесь к администратору за помощью")

        text_channel = member.guild.get_channel(text_channel_id)

        message = await text_channel.send(embed=embed)
        query = ("INSERT INTO lobby_messages (guild_id, message_id, voice_channel_id)"
                 "VALUES ($1, $2, $3)")
        await self.pool.execute(query, member.guild.id,
                                message.id, created_voice_channel.id)

    async def delete_lobby_info(self, member: disnake.Member,
                                voice_channel: disnake.VoiceChannel):
        query = ("SELECT text_channel_id "
                 "FROM lobby_text_channel_ids "
                 "WHERE guild_id = $1 and lobby_category_id = $2")
        text_channel_id = await self.pool.fetchval(query, member.guild.id,
                                                   voice_channel.category.id)

        query = ("SELECT message_id "
                 "FROM lobby_messages "
                 "WHERE guild_id = $1 and voice_channel_id = $2")
        message_id = await self.pool.fetchval(query, member.guild.id,
                                              voice_channel.id)
        text_channel = member.guild.get_channel(text_channel_id)
        if not message_id:
            return

        message = await text_channel.fetch_message(message_id)
        await message.delete()

        query = ("DELETE FROM lobby_messages "
                 "WHERE guild_id = $1 and message_id = $2")
        await self.pool.execute(query, member.guild.id,
                                message_id)
        return True

    # endregion

    async def get_rank_role(self, member,
                            joined_voice_channel):
        query = ("SELECT role_needed "
                 "FROM lobby_category_rank_roles "
                 "WHERE guild_id = $1 and category_id = $2")
        is_role_needed = await self.pool.fetchval(query, member.guild.id,
                                                  joined_voice_channel.category.id)
        if not is_role_needed:
            return "No needed"
        get_guild_rank_query = ("SELECT role_id "
                                "FROM lobby_category_rank_roles "
                                "WHERE guild_id = $1 and category_id = $2")
        result = await self.pool.fetch(get_guild_rank_query, member.guild.id,
                                       joined_voice_channel.category.id)
        guild_rank_roles_ids = []
        for record in result:
            guild_rank_roles_ids.append(record["role_id"])

        if not guild_rank_roles_ids:
            return 1

        user_rank_role = None
        for role in member.roles:
            if role.id in guild_rank_roles_ids:
                user_rank_role = role
                break

        if not user_rank_role:
            return None
        return user_rank_role

    async def create_voice_channel(self, member: disnake.Member,
                                   joined_voice_channel: disnake.VoiceChannel, category_id,
                                   user_limit):
        category = member.guild.get_channel(category_id)
        category_overwrites = category.overwrites
        user_rank_role = await self.get_rank_role(member, joined_voice_channel)

        if user_rank_role == "No needed":
            voice_channel = await member.guild.create_voice_channel(name=f"【🎮】{category.name}", category=category,
                                                                    overwrites=category_overwrites,
                                                                    user_limit=user_limit)
        elif not user_rank_role or user_rank_role == 1:
            voice_channel = await member.guild.create_voice_channel(name=f"【🎮】{category.name}", category=category,
                                                                    overwrites=category_overwrites,
                                                                    user_limit=user_limit)
            if not user_rank_role:
                await voice_channel.send(
                    f"{member.mention}, у Вас не была найдена подходящая роль. Пожалуйста, выберите подходящую для "
                    f"категории роль")
        else:
            voice_channel = await member.guild.create_voice_channel(name=f"【🏆】{user_rank_role.name}", category=category,
                                                                    overwrites=category_overwrites,
                                                                    user_limit=user_limit)

        return voice_channel, user_rank_role

    @staticmethod
    async def create_dashboard(channel):
        embed = (disnake.Embed(title=f"Создан голосовой канал {channel.name}\n"
                                     f"Владелец канала: X"))
        dashboard_buttons = DashboardButtons()
        await channel.send(embed=embed, view=dashboard_buttons)

    # region Condition check

    @staticmethod
    def joined_channel_creator(current, channels_creators_categories_ids):
        if current.channel and current.channel.category.id in channels_creators_categories_ids:
            return True
        return False

    @staticmethod
    def left_channel_creator(before, channels_creators_categories_ids):
        if before.channel and before.channel.category.id in channels_creators_categories_ids:
            return True
        return False

    @staticmethod
    def empty_voice_channel(before):
        if not before.channel.members:
            return True
        return False

    @staticmethod
    def joined_lobby_room(current, categories_ids):
        if current.channel and current.channel.category.id in categories_ids:
            return True
        return False

    @staticmethod
    def left_lobby_room(before, categories_ids):
        if before.channel and before.channel.category.id in categories_ids:
            return True
        return False

    # endregion

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState,
                                    current: disnake.VoiceState):
        if before.channel == current.channel:
            return

        guild_id = member.guild.id
        try:
            get_channel_creators_categories_ids_query = "SELECT category_id " \
                                                        "FROM lobby_voice_creators " \
                                                        "WHERE guild_id = $1"
            result = await self.pool.fetch(get_channel_creators_categories_ids_query, guild_id)
            voice_creators_categories_ids = []
            if not result:
                return
            for record in result:
                if record["category_id"] not in voice_creators_categories_ids:
                    voice_creators_categories_ids.append(record["category_id"])
            if self.left_channel_creator(before, voice_creators_categories_ids):
                return

            get_lobbies_categories_query = ("SELECT lobby_category_id "
                                            "FROM lobby_created_voice_channels_ids "
                                            "WHERE guild_id = $1")
            result = await self.pool.fetch(get_lobbies_categories_query, guild_id)
            if not result:
                return
            lobby_categories_ids = []
            for record in result:
                lobby_categories_ids.append(record["lobby_category_id"])
        except TypeError:
            return

        if self.joined_lobby_room(current, lobby_categories_ids):
            await self.update_lobby_info(current.channel.members, current.channel)

        if self.left_lobby_room(before, lobby_categories_ids):
            if self.empty_voice_channel(before):
                try:
                    if await self.delete_lobby_info(member, before.channel):
                        await before.channel.delete()
                except commands.ChannelNotFound:
                    try:
                        channel = before.channel.guild.get_channel(before.channel.id)
                        if channel:
                            await channel.delete()
                    except Exception as e:
                        logger.error(f"Failed to delete voice channel\nError:{e}")
                except Exception as e:
                    logger.error(f"Failed to delete lobby info or channel\nError: {e}")

            else:
                await self.update_lobby_info(before.channel.members, before.channel)

        if self.joined_channel_creator(current, voice_creators_categories_ids):
            try:
                get_user_limit_query = ("SELECT user_limit "
                                        "FROM lobby_voice_creators "
                                        "WHERE guild_id = $1 and channel_creator_id = $2")
                user_limit = await self.pool.fetchval(get_user_limit_query, guild_id,
                                                      current.channel.id)

                get_lobby_category_id_query = ("SELECT lobby_category_id "
                                               "FROM lobby_created_voice_channels_ids "
                                               "WHERE guild_id = $1 and channel_creator_category_id = $2")
                lobby_category_id = await self.pool.fetchval(get_lobby_category_id_query, guild_id,
                                                             current.channel.category.id)
            except TypeError:
                return

            created_voice_channel, user_rank_role = await self.create_voice_channel(member, current.channel,
                                                                                    lobby_category_id, user_limit)
            try:
                # Channel 1 -> Channel 2
                # Current channel: Channel 1
                await member.move_to(created_voice_channel)
                # Current channel: Channel 2
            except disnake.errors.HTTPException:
                await created_voice_channel.delete()
                return
            if not created_voice_channel:
                print("Created channel cannot be found")
                return
            await asyncio.sleep(1)
            if created_voice_channel.members:
                embed = self.create_lobby_info(member, user_rank_role,
                                               created_voice_channel, created_voice_channel.user_limit)
                await self.send_lobby_info(member, created_voice_channel,
                                           embed)
                await self.create_dashboard(created_voice_channel)
            elif not created_voice_channel.members:
                try:
                    await self.delete_lobby_info(member, created_voice_channel)
                    await created_voice_channel.delete()
                except disnake.errors.NotFound:
                    pass


def setup(bot):
    bot.add_cog(LobbyChannels(bot))
