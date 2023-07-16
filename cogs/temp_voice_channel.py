import typing
import disnake
from disnake.ext import commands
import asyncpg
from core.bot import Nexus
import time


class OnJoinChannel(commands.Cog):
    def __init__(self, bot: Nexus):
        self.custom_channel: typing.Optional[disnake.VoiceChannel] = None
        self.bot = bot
        self.pool: asyncpg.Pool = bot.get_pool()
        self.category_id = None
        self.channel_creator_id = None
        self.created_channels_ids = []
        self.custom_channel_name = None

    async def create_voice_channel(
            self,
            member: disnake.Member,
            channel_name: str = None,

    ):
        category = member.guild.get_channel(self.category_id)

        channel_name = channel_name or f"{member.name}'s channel"
        voice_channel = await member.guild.create_voice_channel(
            name=channel_name,
            category=category,
            overwrites=category.overwrites
        )
        self.created_channels_ids.append(voice_channel.id)
        overwrite = disnake.PermissionOverwrite(
            view_channel=True,
            manage_permissions=True,
            manage_channels=True
        )
        await voice_channel.set_permissions(member, overwrite=overwrite)

        await member.move_to(voice_channel)

        return voice_channel

    @commands.Cog.listener()
    async def on_voice_state_update(
            self,
            member: disnake.Member,
            before: disnake.VoiceState,
            current: disnake.VoiceState,
    ):
        if before.channel == current.channel:
            return

        guild_id = member.guild.id
        try:
            query = "SELECT voice_channel_category_id, create_voice_channel_id " \
                    "FROM guild_settings " \
                    "WHERE guild_id = $1"
            self.category_id, self.channel_creator_id = await self.pool.fetchrow(query, guild_id)

            query = "SELECT created_voice_channel_ids " \
                    "FROM guild_settings " \
                    "WHERE guild_id = $1"
            result = await self.pool.fetchval(query, guild_id)
            if result:
                self.created_channels_ids = list(result)

        except:
            pass

        if current.channel is not None and current.channel.id == self.channel_creator_id:
            # TODO: получить разрешения ролей и участников из БД

            try:
                query = "SELECT channel_name " \
                        "FROM custom_voice " \
                        "WHERE guild_id_user_id = $1"
                self.custom_channel_name = await self.pool.fetchval(query, f"{member.guild.id}_{member.id}")
            except:
                pass

            self.custom_channel = await self.create_voice_channel(
                member=member,
                channel_name=self.custom_channel_name,
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
                # TODO: сохранить разрешения канала в БД
                # overwrites = before.channel.overwrites
                self.custom_channel_name = before.channel.name

                query = "INSERT INTO custom_voice (guild_id_user_id, channel_name)" \
                        "VALUES ($1, $2)" \
                        "ON CONFLICT (guild_id_user_id) " \
                        "DO UPDATE SET channel_name = $2"
                await self.pool.execute(query, f"{member.guild.id}_{member.id}", self.custom_channel_name)

                query = "UPDATE guild_settings SET " \
                        "created_voice_channel_ids = array_remove(created_voice_channel_ids, $2) " \
                        "WHERE guild_id = $1"
                await self.pool.execute(
                    query,
                    member.guild.id,
                    before.channel.id
                )
                self.created_channels_ids.remove(before.channel.id)
                await before.channel.delete()

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
                #         "SET custom_channel_name = $2, permissions = $3 " \
                #         "WHERE channel_creator_id = $1"
                # await self.pool.execute(query, member.id, self.custom_channel_name, self.permissions)


def setup(bot):
    bot.add_cog(OnJoinChannel(bot))
