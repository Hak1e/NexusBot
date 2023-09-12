import disnake
from disnake.ext import commands
import asyncpg
from core.bot import Nexus
import json


class OnJoinChannel(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.get_pool()

    async def create_voice_channel(self, member: disnake.Member, category_id):
        query = "SELECT channel_name, bitrate, user_limit " \
                "FROM custom_voice " \
                "WHERE guild_id = $1 and user_id = $2"
        result = await self.pool.fetchrow(query, member.guild.id,
                                          member.id)
        custom_channel_name = None
        bitrate = 64000
        user_limit = 0
        if result:
            result = dict(result)
            custom_channel_name = result.get("channel_name", None)
            bitrate = result.get("bitrate", 64000)
            user_limit = result.get("user_limit", 0)

        category = member.guild.get_channel(category_id)
        category_overwrites = category.overwrites
        initial_category_overwrites = category.overwrites.copy()
        member_overwrite = disnake.PermissionOverwrite(
            view_channel=True,
            connect=True,
            manage_channels=True,
            move_members=True
        )

        get_channel_overwrites = ("SELECT channel_overwrites "
                                  "FROM custom_voice "
                                  "WHERE guild_id = $1 and user_id = $2")
        channel_overwrites = await self.pool.fetchval(get_channel_overwrites, member.guild.id,
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

        category_overwrites.update(initial_category_overwrites)

        channel_name = custom_channel_name or f"{member.name}'s channel"
        voice_channel = await member.guild.create_voice_channel(name=channel_name, category=category,
                                                                overwrites=category_overwrites, bitrate=bitrate,
                                                                user_limit=user_limit)
        query = "INSERT INTO custom_voice (guild_id, user_id, channel_id)" \
                "VALUES ($1, $2, $3)" \
                "ON CONFLICT (guild_id, user_id) DO UPDATE " \
                "SET channel_id = $3"
        await self.pool.execute(query, member.guild.id,
                                member.id, voice_channel.id)

        try:
            await member.move_to(voice_channel)
        except disnake.errors.HTTPException:
            await self.delete_voice_channel(member, voice_channel)

        return

    async def delete_voice_channel(self, member: disnake.Member, channel: disnake.VoiceChannel):
        get_channel_author_id = "SELECT user_id " \
                                "FROM custom_voice " \
                                "WHERE guild_id = $1 and channel_id = $2"
        channel_author_id = await self.pool.fetchval(get_channel_author_id, member.guild.id,
                                                     channel.id)

        channel_overwrites = channel.overwrites
        data = []
        for target, permissions in channel_overwrites.items():
            data.append(
                {
                    "target": target.id,
                    "permissions": dict(permissions)
                }
            )
        json_data = json.dumps(data)
        update_channel_settings = ("INSERT INTO custom_voice ("
                                   "guild_id, user_id, "
                                   "channel_id, channel_name, "
                                   "channel_overwrites, bitrate, "
                                   "user_limit) "
                                   "VALUES ($1, $2, $3, $4, $5, $6, $7)"
                                   "ON CONFLICT (guild_id, user_id) DO UPDATE "
                                   "SET channel_id = $3, channel_name = $4, "
                                   "channel_overwrites = $5, bitrate = $6, "
                                   "user_limit = $7")
        await self.pool.execute(update_channel_settings, member.guild.id,
                                channel_author_id, None,
                                channel.name, json_data,
                                channel.bitrate, channel.user_limit)

        await channel.delete()
        return

    async def edit_channel_settings(self):
        pass
        # TODO: дать пользователю возможность выбрать участника/роль, затем действие. Запретить изменять участников/роли, которые есть в категории

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState,
                                    current: disnake.VoiceState):
        if before.channel == current.channel:
            return

        guild_id = member.guild.id
        query = "SELECT voice_channel_category_id, channel_creator_id " \
                "FROM guild_settings " \
                "WHERE guild_id = $1"
        try:
            category_id, channel_creator_id = await self.pool.fetchrow(query, guild_id)
        except TypeError:
            return

        if before.channel and before.channel.category.id == category_id\
                and before.channel.id != channel_creator_id\
                and not before.channel.members:
            await self.delete_voice_channel(member, before.channel)

        if current.channel and current.channel.id == channel_creator_id:
            await self.create_voice_channel(member, category_id)


def setup(bot):
    bot.add_cog(OnJoinChannel(bot))
