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

    async def create_voice_channel(
            self,
            member: disnake.Member,
    ):
        category = member.guild.get_channel(self.category_id)
        overwrite = disnake.PermissionOverwrite(
            view_channel=True,
            manage_permissions=True,
            manage_channels=True
        )

        text_channel = await member.guild.create_voice_channel(
            name=f"{member.name}'s channel",
            category=category,
            overwrites=category.overwrites
        )
        self.created_channels_ids.append(text_channel.id)
        await text_channel.set_permissions(member, overwrite=overwrite)

        await member.move_to(text_channel)

        return text_channel

    async def voice_state_log(
            self,
            member: disnake.Member,
            before: disnake.VoiceState,
            current: disnake.VoiceState,
    ):
        if before.channel is None and current.channel is not None:
            print(f"{member.name} зашёл в {current.channel.name}")

        elif before.channel is not None and current.channel is not None:
            previous_channel_name = before.channel.name
            print(f"{member.name} перешёл из {previous_channel_name} в {current.channel.name}")

        elif before.channel is not None and current.channel is None:
            print(f"{member.name} покинул канал {before.channel.name}")

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
            try:
                await self.load_settings(guild_id)
                await self.load_created_channels(guild_id)

                self.guild_settings_loaded[guild_id] = True
                # print(f"Настройки для сервера {member.guild.name} загружены")
            except Exception as e:
                # print(f"Не удалось загрузить настройки сервера. Ошибка: {e}")
                pass

        if before.channel == current.channel:
            return

        # await self.voice_state_log(
        #     member=member,
        #     before=before,
        #     current=current
        # )

        if current.channel is not None and current.channel.id == self.create_channel_id:
            self.custom_channel = await self.create_voice_channel(member=member)
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
                await before.channel.delete()
                self.created_channels_ids.remove(before.channel.id)

                query = "UPDATE guild_settings SET " \
                        "created_voice_channel_ids = array_remove(created_voice_channel_ids, $2) " \
                        "WHERE guild_id = $1"
                await self.pool.execute(
                    query,
                    member.guild.id,
                    before.channel.id
                )


def setup(bot):
    bot.add_cog(OnJoinChannel(bot))
