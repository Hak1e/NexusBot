import asyncpg
import json
import disnake
import enum
import asyncio


class AuthorSettings:
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.get_pool()

    async def get_voice_channel_author_id(self, voice_channel):
        get_channel_author_id = "SELECT user_id " \
                                "FROM lobby_voice_channel_author " \
                                "WHERE voice_channel_id = $1"
        channel_author_id = await self.pool.fetchval(get_channel_author_id, voice_channel.id)
        return channel_author_id

    async def update_voice_channel_name(self, voice_channel):
        channel_author_id = await self.get_voice_channel_author_id(voice_channel)
        update_channel_settings = ("INSERT INTO lobby_voice_channel_settings ("
                                   "user_id, guild_id,"
                                   "channel_name) "
                                   "VALUES ($1, $2, $3)"
                                   "ON CONFLICT (guild_id, user_id) DO UPDATE "
                                   "SET channel_name = $3")
        await self.pool.execute(update_channel_settings, channel_author_id,
                                voice_channel.guild.id, voice_channel.name)

    async def update_voice_channel_limit(self, voice_channel):
        channel_author_id = await self.get_voice_channel_author_id(voice_channel)
        update_channel_settings = ("INSERT INTO lobby_voice_channel_settings ("
                                   "user_id, guild_id,"
                                   "user_limit) "
                                   "VALUES ($1, $2, $3)"
                                   "ON CONFLICT (guild_id, user_id) DO UPDATE "
                                   "SET user_limit = $3")
        await self.pool.execute(update_channel_settings, channel_author_id,
                                voice_channel.guild.id, voice_channel.user_limit)

    async def update_voice_channel_bitrate(self, voice_channel):
        channel_author_id = await self.get_voice_channel_author_id(voice_channel)
        update_channel_settings = ("INSERT INTO lobby_voice_channel_settings ("
                                   "user_id, guild_id,"
                                   "bitrate) "
                                   "VALUES ($1, $2, $3)"
                                   "ON CONFLICT (guild_id, user_id) DO UPDATE "
                                   "SET bitrate = $3")
        await self.pool.execute(update_channel_settings, channel_author_id,
                                voice_channel.guild.id, voice_channel.bitrate)

    async def update_voice_channel_overwrites(self, voice_channel):
        channel_author_id = await self.get_voice_channel_author_id(voice_channel)
        channel_overwrites = voice_channel.overwrites
        data = []
        for target, permissions in channel_overwrites.items():
            data.append(
                {
                    "target": target.id,
                    "permissions": dict(permissions)
                }
            )
        channel_overwrites_json = json.dumps(data)
        update_channel_settings = ("INSERT INTO lobby_voice_channel_settings ("
                                   "user_id, guild_id,"
                                   "channel_overwrites) "
                                   "VALUES ($1, $2, $3)"
                                   "ON CONFLICT (guild_id, user_id) DO UPDATE "
                                   "SET channel_overwrites = $3")
        await self.pool.execute(update_channel_settings, channel_author_id,
                                voice_channel.guild.id, channel_overwrites_json)


class RequestedRole(str, enum.Enum):
    not_found = "not_found"
    not_needed = "not_needed"
    missing = "missing"


class LobbyChannelSettings:
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = self.bot.get_pool()

    @staticmethod
    async def update_lobby_info_message(message, voice_channel):
        new_embed = message.embeds[0]
        member_enumeration = []
        counter = 1
        for member in voice_channel.members:
            member_enumeration.append(f"【{counter}】{member.mention}")
            counter += 1

        member_list = "\n".join(member_enumeration)
        new_embed.set_field_at(0, name="", value=f"{member_list}\n")
        user_limit = voice_channel.user_limit
        if user_limit == 0:
            user_limit = "∞"
        if len(voice_channel.members) >= voice_channel.user_limit != 0:
            new_embed.set_field_at(1, name="",
                                   value="\n**❌ Канал заполнен**", inline=False)
        else:
            new_embed.set_field_at(1, name="",
                                   value=f"\n**✅ Канал:** {voice_channel.mention}", inline=False)
        new_embed.set_footer(text=f"Участников: {len(voice_channel.members)}/{user_limit}")
        await message.edit(embed=new_embed)

    # region Get

    async def get_channel_creator_id(self, lobby_voice_channel_id):
        query = ("SELECT voice_creator_id "
                 "FROM lobby_created_voice_channel "
                 "WHERE id = $1")
        return await self.pool.fetchval(query, lobby_voice_channel_id)

    async def get_text_channel_id(self, voice_channel_creator_id):
        query = ("SELECT text_channel_id "
                 "FROM lobby_voice_channel_creator_settings "
                 "WHERE id = $1")
        return await self.pool.fetchval(query, voice_channel_creator_id)

    async def get_lobby_message_id(self, voice_channel):
        query = ("SELECT id "
                 "FROM lobby_message "
                 "WHERE voice_channel_id = $1")
        message_id = await self.pool.fetchval(query, voice_channel.id)
        return message_id

    async def get_lobby_info_message(self, voice_channel):
        message_id = await self.get_lobby_message_id(voice_channel)
        if not message_id:
            return
        channel_creator_id = await self.get_channel_creator_id(voice_channel.id)
        if not channel_creator_id:
            return
        text_channel_id = await self.get_text_channel_id(channel_creator_id)
        if not text_channel_id:
            return
        message = await self.get_message_from_discord(voice_channel, message_id,
                                                      text_channel_id)
        return message or None

    async def get_message_from_discord(self, voice_channel: disnake.VoiceChannel,
                                       message_id, text_channel_id,
                                       row=0):
        if row == 4:
            return
        try:
            text_channel = voice_channel.guild.get_channel(text_channel_id)
            message = await text_channel.fetch_message(message_id)
            # if not message:
            #     # Когда Дискорд нестабилен, бот может не получить запрашиваемое сообщение.
            #     # Поэтому делаем 3 попытки получить сообщение.
            #     for i in range(3):
            #         message = await text_channel.fetch_message(message_id)
            #         if message:
            #             break
            #         await asyncio.sleep(1)
            return message
        except disnake.errors.NotFound:
            await asyncio.sleep(1)
            message = await self.get_message_from_discord(voice_channel, message_id,
                                                          text_channel_id, row + 1)
            return message or None

    async def get_custom_channel_settings(self, guild_id,
                                          member):
        query = ("SELECT channel_name, bitrate, user_limit "
                 "FROM lobby_voice_channel_settings "
                 "WHERE guild_id = $1 and user_id = $2")
        result = await self.pool.fetchrow(query, guild_id,
                                          member.id)
        custom_channel_name = None
        bitrate = 64000
        user_limit = 0
        if result:
            custom_channel_name = result.get("channel_name", None)
            bitrate = result.get("bitrate", 64000)
            user_limit = result.get("user_limit", 0)

        return custom_channel_name, bitrate, user_limit

    async def get_voice_channel_author_id(self, voice_channel):
        get_channel_author_id = "SELECT user_id " \
                                "FROM lobby_voice_channel_author " \
                                "WHERE voice_channel_id = $1"
        channel_author_id = await self.pool.fetchval(get_channel_author_id, voice_channel.id)
        return channel_author_id

    async def get_channel_overwrites(self, category,
                                     member):
        initial_category_overwrites = category.overwrites
        category_overwrites = category.overwrites.copy()
        member_overwrite = disnake.PermissionOverwrite(view_channel=True, connect=True,
                                                       move_members=True)
        query = ("SELECT channel_overwrites "
                 "FROM lobby_voice_channel_settings "
                 "WHERE guild_id = $1 and user_id = $2")
        channel_overwrites = await self.pool.fetchval(query, member.guild.id,
                                                      member.id)
        if channel_overwrites:
            channel_overwrites = json.loads(channel_overwrites)
            for target_id_permissions in channel_overwrites:
                target_id = target_id_permissions["target"]
                permissions = target_id_permissions["permissions"]
                target = member.guild.get_member(target_id) or member.guild.get_role(target_id)

                permission_overwrite = disnake.PermissionOverwrite()
                for permission, value in permissions.items():
                    setattr(permission_overwrite, permission, value)

                category_overwrites[target] = permission_overwrite
        else:
            category_overwrites[member] = member_overwrite

        category_overwrites[self.bot.user] = member_overwrite
        category_overwrites.update(initial_category_overwrites)

        return category_overwrites

    async def get_channel_required_role(self, member,
                                        channel_id):
        query = ("SELECT role_needed "
                 "FROM lobby_voice_channel_creator_settings "
                 "WHERE id = $1")
        role_required = await self.pool.fetchval(query, channel_id)
        if not role_required:
            return RequestedRole.not_needed

        get_role_required_query = ("SELECT role_id "
                                   "FROM lobby_voice_channel_creator_role "
                                   "WHERE voice_channel_id = $1")
        result = await self.pool.fetch(get_role_required_query, channel_id)
        required_roles_ids = []
        if result:
            for record in result:
                required_roles_ids.append(record["role_id"])

        if not required_roles_ids:
            return RequestedRole.not_found

        user_required_role = None
        for role in member.roles:
            if role.id in required_roles_ids:
                user_required_role = role
                break

        if not user_required_role:
            return RequestedRole.missing
        return user_required_role

    # endregion

    async def log_needed(self, voice_channel_id):
        query = ("SELECT log_needed "
                 "FROM lobby_voice_channel_creator_settings "
                 "WHERE id = $1")
        return await self.pool.fetchval(query, int(voice_channel_id))

    async def save_message_id_to_db(self, voice_channel,
                                    message):
        query = ("INSERT INTO lobby_message (id, voice_channel_id)"
                 "VALUES ($1, $2)")
        await self.pool.execute(query, message.id,
                                voice_channel.id)

    async def delete_message_id_from_db(self, message_id):
        query = ("DELETE FROM lobby_message "
                 "WHERE id = $1")
        await self.pool.execute(query, message_id)

    async def set_voice_channel_author_id(self, member,
                                          voice_channel):
        query = ("INSERT INTO lobby_voice_channel_author(voice_channel_id, user_id) "
                 "VALUES ($1, $2)")
        await self.pool.execute(query, voice_channel.id,
                                member.id)

    async def delete_voice_channel_author_id(self, voice_channel):
        query = ("DELETE FROM lobby_voice_channel_author "
                 "WHERE voice_channel_id = $1")
        await self.pool.execute(query, voice_channel.id)

    async def delete_created_voice_channel_from_db(self, voice_channel):
        query = ("DELETE FROM lobby_created_voice_channel "
                 "WHERE id = $1")
        await self.pool.execute(query, voice_channel.id)

    async def add_lobby_channel_to_db(self, created_channel_id,
                                      channel_creator_id):
        query = ("INSERT INTO lobby_created_voice_channel (id, voice_creator_id) "
                 "VALUES ($1, $2)")
        await self.pool.execute(query, created_channel_id,
                                channel_creator_id)

    async def is_custom(self, channel_id):
        query = ("SELECT voice_creator_id "
                 "FROM lobby_created_voice_channel "
                 "WHERE id = $1")
        voice_creator_id = await self.pool.fetchval(query, channel_id)
        if not voice_creator_id:
            return
        query = ("SELECT custom "
                 "FROM lobby_voice_channel_creator_settings "
                 "WHERE id = $1")
        return await self.pool.fetchval(query, voice_creator_id)
