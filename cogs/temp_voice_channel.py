import json
import typing

import disnake
from disnake.ext import commands
from disnake import Permissions
import config
import asyncpg
from core.bot import Nexus


class OnJoinChannel(commands.Cog):
    def __init__(self, bot: Nexus):
        self.custom_channel: typing.Optional[disnake.VoiceChannel] = None
        self.bot = bot
        self.pool: asyncpg.Pool = bot.get_pool()
        self.category_id = None
        self.create_channel_id = None
        self.guild_settings_loaded = {}
        self.created_channels_ids = []
        self.channel_name = None
        self.permissions = None

    async def create_voice_channel(
            self,
            member: disnake.Member,
            channel_name: str = None,
            overwrites=None

    ):
        category = member.guild.get_channel(self.category_id)
        overwrite = disnake.PermissionOverwrite(
            view_channel=True,
            manage_permissions=True,
            manage_channels=True
        )

        channel_name = channel_name or f"{member.name}'s channel"
        voice_channel = await member.guild.create_voice_channel(
            name=channel_name,
            category=category,
            overwrites=category.overwrites
        )
        self.created_channels_ids.append(voice_channel.id)
        await voice_channel.set_permissions(member, overwrite=overwrites or overwrite)

        await member.move_to(voice_channel)

        return voice_channel

    async def load_settings(self, guild_id):
        async with self.pool.acquire() as conn:
            query = "SELECT voice_channel_category_id, create_voice_channel_id " \
                    "FROM guild_settings " \
                    "WHERE guild_id = $1"

            self.category_id, self.create_channel_id = await conn.fetchrow(query, guild_id)
            # print(f"Loaded settings for guild id {guild_id}\nCategroy id: {self.category_id}\nChannel id: {self.create_channel_id}")

    async def load_created_channels(self, guild_id):
        query = "SELECT created_voice_channel_ids " \
                "FROM guild_settings " \
                "WHERE guild_id = $1"

        result = await self.pool.fetchval(query, guild_id)
        if result:
            self.created_channels_ids = list(result)

    async def unload_guild_settings(self, guild_id):
        self.guild_settings_loaded[guild_id] = False

    @commands.Cog.listener()
    async def on_voice_state_update(
            self,
            member: disnake.Member,
            before: disnake.VoiceState,
            current: disnake.VoiceState,
    ):
        guild_id = member.guild.id

        if guild_id not in self.guild_settings_loaded:
            self.guild_settings_loaded[guild_id] = False

        if not self.guild_settings_loaded[guild_id]:
            try:
                await self.load_settings(guild_id)
                await self.load_created_channels(guild_id)

                self.guild_settings_loaded[guild_id] = True
            except:
                pass

        if before.channel == current.channel:
            return

        if current.channel is not None and current.channel.id == self.create_channel_id:
            # TODO: получить имя канала из базы данных, если оно есть

            # try:
            #     query = "SELECT channel_name, permissions " \
            #             "FROM custom_voice " \
            #             "WHERE channel_creator_id = $1"
            #     self.channel_name, self.permissions = await self.pool.fetchrow(query, member.id)
            #     print(f"Channel name: {self.channel_name}\nPermissions: {self.permissions}")
            # except:
            #     pass



            self.custom_channel = await self.create_voice_channel(
                member=member,
                channel_name=self.channel_name,
                overwrites=self.permissions
            )
            query = "UPDATE guild_settings " \
                    "SET created_voice_channel_ids = array_append(created_voice_channel_ids, $2) " \
                    "WHERE guild_id = $1"
            await self.pool.execute(
                query,
                member.guild.id,
                self.custom_channel.id
            )





        if before.channel is not None and before.channel.id in self.created_channels_ids:
            if not before.channel.members:
                # TODO: сохранить имя кнала в базу данных
                # overwrites = before.channel.overwrites
                # self.channel_name = before.channel.name

                query = "UPDATE guild_settings SET " \
                        "created_voice_channel_ids = array_remove(created_voice_channel_ids, $2) " \
                        "WHERE guild_id = $1"
                await self.pool.execute(
                    query,
                    member.guild.id,
                    before.channel.id
                )
                await before.channel.delete()
                self.created_channels_ids.remove(before.channel.id)


                # data = []
                # for target, permissions in overwrites.items():
                #     data.append(
                #         {
                #             "target": target.id,
                #             "permissions": dict(permissions)
                #         }
                #     )
                #
                #
                #
                # query = "UPDATE custom_voice " \
                #         "SET channel_name = $2, permissions = $3 " \
                #         "WHERE channel_creator_id = $1"
                # await self.pool.execute(query, member.id, self.channel_name, self.permissions)

def setup(bot):
    bot.add_cog(OnJoinChannel(bot))
