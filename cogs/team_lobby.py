import time

import disnake
from disnake.ext import commands
import asyncpg
from core.bot import Nexus


class LobbyChannels(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.get_pool()

    @staticmethod
    def create_lobby_info(role: disnake.Role, member,
                          voice_channel: disnake.VoiceChannel, user_limit):
        if user_limit == 0:
            user_limit = "∞"
        # role_icon = f"<:{role.name}:{role.id}>" if role else "NET"
        embed = (
            disnake.Embed(title="**Участники:**", color=role.color)
            .add_field("", f"【1】{member.mention}\n")
            .add_field("", f"\n**✅ Канал:** {voice_channel.mention}",
                       inline=False)
            .set_thumbnail(role.icon.url if role.icon else None)
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
                 "FROM rating_lobby_text_channel_id "
                 "WHERE guild_id = $1")
        text_channel_id = await self.pool.fetchval(query, voice_channel.guild.id)

        if message_id is None or text_channel_id is None:
            return

        text_channel = voice_channel.guild.get_channel(text_channel_id)
        message: disnake.Message = await text_channel.fetch_message(message_id)
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
        if len(voice_channel.members) == voice_channel.user_limit:
            updated_embed.set_field_at(1, name="", value="**❌ Канал заполнен**",
                                       inline=False)
        else:
            updated_embed.set_field_at(1, "", f"\n**✅ Канал:** {voice_channel.mention}",
                                       inline=False)
        updated_embed.set_footer(text=f"Участников: {len(members)}/{user_limit}")
        await message.edit(embed=updated_embed)

    async def send_lobby_info(self, member: disnake.Member,
                              role: disnake.Role, voice_channel: disnake.VoiceChannel,
                              created_voice_channel, user_limit,
                              created_voice_channel_id):
        text_channel_id_query = ("SELECT text_channel_id "
                                 "FROM rating_lobby_text_channel_id "
                                 "WHERE guild_id = $1")
        text_channel_id = await self.pool.fetchval(text_channel_id_query, member.guild.id)
        if not text_channel_id:
            return await voice_channel.send(f"{member.mention}, "
                                                   f"Оповещение о создании комнаты не было создано из-за неверных настроек. Обратитесь к администратору за помощью")

        text_channel = member.guild.get_channel(text_channel_id)
        embed = self.create_lobby_info(role, member,
                                       created_voice_channel, user_limit)
        message = await text_channel.send(embed=embed)
        query = ("INSERT INTO lobby_messages (guild_id, message_id, voice_channel_id)"
                 "VALUES ($1, $2, $3)")
        await self.pool.execute(query, member.guild.id, message.id, created_voice_channel_id)

    async def delete_lobby_info(self, member: disnake.Member,
                                voice_channel: disnake.VoiceChannel):
        query = ("SELECT text_channel_id "
                 "FROM rating_lobby_text_channel_id "
                 "WHERE guild_id = $1")
        text_channel_id = await self.pool.fetchval(query, member.guild.id)

        query = ("SELECT message_id "
                 "FROM lobby_messages "
                 "WHERE guild_id = $1 and voice_channel_id = $2")
        message_id = await self.pool.fetchval(query, member.guild.id, voice_channel.id)
        text_channel = member.guild.get_channel(text_channel_id)
        try:
            message = await text_channel.fetch_message(message_id)
            await message.delete()
        except:
            pass

        query = ("DELETE FROM lobby_messages "
                 "WHERE guild_id = $1 and message_id = $2")
        await self.pool.execute(query, member.guild.id, message_id)

    async def get_rank_role(self, member,
                            joined_voice_channel):
        get_guild_rank_query = ("SELECT role_id "
                                "FROM rank_roles "
                                "WHERE guild_id = $1")
        result = await self.pool.fetch(get_guild_rank_query, member.guild.id)
        guild_rank_roles_ids = []
        for record in result:
            guild_rank_roles_ids.append(record["role_id"])

        if not guild_rank_roles_ids:
            message = await joined_voice_channel.send(f"{member.mention}, "
                                                      f"не удалось создать комнату из-за отсутствия информации о ролях в базе данных. Обратитесь к администратору")
            await message.delete(delay=15)
            await member.move_to(None, reason="Не удалось получить роль из базы данных для создания рейтинговой комнаты")  # type: ignore
            return

        user_rank_role = None
        for role in member.roles:
            if role.id in guild_rank_roles_ids:
                user_rank_role = role
                break

        if not user_rank_role:
            return False
        return user_rank_role

    async def create_voice_channel(self, member: disnake.Member,
                                   joined_voice_channel: disnake.VoiceChannel, category_id,
                                   user_limit):
        category = member.guild.get_channel(category_id)
        category_overwrites = category.overwrites
        user_rank_role = await self.get_rank_role(member, joined_voice_channel)
        if not user_rank_role:
            message = await joined_voice_channel.send(f"{member.mention}, "
                                                      f"выберите соответствующую роль для создания канала")
            await message.delete(delay=15)
            await member.move_to(None, reason="Нет роли для создания рейтинговой комнаты")  # type: ignore
            return

        voice_channel = await member.guild.create_voice_channel(name=f"【🏆】{user_rank_role.name}", category=category,  # type: ignore
                                                                overwrites=category_overwrites, user_limit=user_limit)

        try:
            await member.move_to(voice_channel)
        except disnake.errors.HTTPException:
            await self.delete_voice_channel(voice_channel)

        await self.send_lobby_info(member, user_rank_role,  # type: ignore
                                   joined_voice_channel, voice_channel,
                                   user_limit, voice_channel.id)

    @staticmethod
    async def delete_voice_channel(channel: disnake.VoiceChannel):
        await channel.delete()

    # region Condition check

    @staticmethod
    def joined_channel_creator(current, channels_creators_category):
        if current.channel and current.channel.category.id == channels_creators_category:
            return True
        return False

    @staticmethod
    def left_channel_creator(before, channels_creators_category):
        if before.channel and before.channel.category.id == channels_creators_category:
            return True
        return False

    @staticmethod
    def empty_voice_channel(before):
        if not before.channel.members:
            return True
        return False

    @staticmethod
    def joined_lobby_room(current, category_id):
        if current.channel and current.channel.category.id == category_id:
            return True
        return False

    @staticmethod
    def left_lobby_room(before, category_id):
        if before.channel and before.channel.category.id == category_id:
            return True
        return False

    # endregion

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState,
                                    current: disnake.VoiceState):
        if before.channel == current.channel:
            return

        guild_id = member.guild.id
        get_category_id_query = "SELECT category_id " \
                                "FROM voice_creators " \
                                "WHERE guild_id = $1"

        get_lobby_category_id_query = ("SELECT category_id "
                                       "FROM created_lobbies_category_id "
                                       "WHERE guild_id = $1")

        try:
            voice_creators_category_id = await self.pool.fetchval(get_category_id_query, guild_id)
            lobby_category_id = await self.pool.fetchval(get_lobby_category_id_query, guild_id)
        except TypeError:
            return

        if self.left_channel_creator(before, voice_creators_category_id):
            return

        if self.joined_channel_creator(current, voice_creators_category_id):
            get_user_limit_query = ("SELECT user_limit "
                                    "FROM voice_creators "
                                    "WHERE guild_id = $1 and channel_creator_id = $2")
            user_limit = await self.pool.fetchval(get_user_limit_query, guild_id, current.channel.id)

            await self.create_voice_channel(member, current.channel, lobby_category_id, user_limit)
        if self.joined_lobby_room(current, lobby_category_id):
            await self.update_lobby_info(current.channel.members, current.channel)

        if self.left_lobby_room(before, lobby_category_id):
            if self.empty_voice_channel(before):
                await self.delete_voice_channel(before.channel)
                await self.delete_lobby_info(member, before.channel)
            else:
                await self.update_lobby_info(before.channel.members, before.channel)


def setup(bot):
    bot.add_cog(LobbyChannels(bot))
