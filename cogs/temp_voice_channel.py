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
        self.settings_loaded = False
        self.created_channels_ids = []

    async def create_voice_channel(
            self,
            member: disnake.Member,
    ):
        category = member.guild.get_channel(self.category_id)
        # bot = member.guild.get_member(self.bot.user.id)
        overwrite = disnake.PermissionOverwrite(
            view_channel=True,
            manage_permissions=True,
            manage_channels=True
        )

        channel = await member.guild.create_voice_channel(
            name=f"{member.name}'s channel",
            category=category,
            overwrites=category.overwrites
        )
        self.created_channels_ids.append(channel.id)
        await channel.set_permissions(member, overwrite=overwrite)

        await member.move_to(channel)

        return channel

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
            query = "SELECT temp_voice_channel_category_id, temp_create_voice_channel FROM guild_settings WHERE guild_id = $1"
            self.category_id, self.create_channel_id = await conn.fetchrow(query, guild_id)

    async def load_created_channels(self, member: disnake.Member):
        query = "SELECT temp_voice_channel_id FROM guild_settings WHERE guild_id = $1"
        result = await self.pool.fetchval(query, member.guild.id)
        if result:
            self.created_channels_ids = list(result)
            # print(self.created_channels_ids)
        else:
            print("Столбец temp_voice_channel_id пуст")

    @commands.Cog.listener()
    async def on_voice_state_update(
            self,
            member: disnake.Member,
            before: disnake.VoiceState,
            current: disnake.VoiceState,
    ):

        if not self.settings_loaded:
            try:
                await self.load_settings(member.guild.id)
                await self.load_created_channels(member)
                # print("Настройки загружены")
                self.settings_loaded = True
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
            query = "UPDATE guild_settings SET temp_voice_channel_id = array_append(temp_voice_channel_id, $2) WHERE guild_id = $1"
            await self.pool.execute(
                query,
                member.guild.id,
                self.custom_channel.id
            )
            print("Созданный канал добавлен в БД")


        if before.channel is not None and before.channel.id in self.created_channels_ids:
            if not before.channel.members:
                await before.channel.delete()
                self.created_channels_ids.remove(before.channel.id)

                query = "UPDATE guild_settings SET temp_voice_channel_id = array_remove(temp_voice_channel_id, $2) WHERE guild_id = $1"
                await self.pool.execute(
                    query,
                    member.guild.id,
                    before.channel.id
                )
                print("Созданный канал удалён из БД")


def setup(bot):
    bot.add_cog(OnJoinChannel(bot))
