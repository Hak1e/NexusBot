import typing
import disnake
from disnake.ext import commands
import asyncpg
from core.bot import Nexus


class OnJoinChannel(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.get_pool()
        self.category_id = None
        self.channel_creator_id = None
        self.created_channels_ids = []
        self.custom_channel_name = None

    async def create_voice_channel(self, member: disnake.Member):
        query = "SELECT channel_name " \
                "FROM custom_voice " \
                "WHERE guild_id = $1 and user_id = $2"
        self.custom_channel_name = await self.pool.fetchval(query, member.guild.id, member.id)
        print(f"Custom name for {member}: {self.custom_channel_name}")
        category = member.guild.get_channel(self.category_id)
        channel_name = self.custom_channel_name or f"{member.name}'s channel"

        voice_channel = await member.guild.create_voice_channel(
            name=channel_name, category=category, overwrites=category.overwrites
        )

        self.created_channels_ids.append(voice_channel.id)
        query = "UPDATE guild_settings " \
                "SET created_voice_channel_ids = array_append(created_voice_channel_ids, $2) " \
                "WHERE guild_id = $1"
        await self.pool.execute(query, member.guild.id, voice_channel.id)

        category_ow = category.overwrites
        if member in category_ow:
            category_ow[member].update(
                view_channel=True, manage_channels=True, manage_permissions=True, move_members=True)
            await voice_channel.edit(overwrites=category_ow)
        else:
            await voice_channel.set_permissions(
                member, view_channel=True, manage_channels=True, manage_permissions=True, move_members=True)

        await member.move_to(voice_channel)

        return

    async def delete_voice_channel(self, member: disnake.Member, before: disnake.VoiceState):
        self.custom_channel_name = before.channel.name
        # TODO: узнать автора канала и присвоить имя конкретно для него, а не последнего вышедшего из канала
        query = "INSERT INTO custom_voice (guild_id, user_id, channel_name)" \
                "VALUES ($1, $2, $3)" \
                "ON CONFLICT (guild_id, user_id) " \
                "DO UPDATE SET channel_name = $3"
        await self.pool.execute(query, member.guild.id, member.id, self.custom_channel_name)

        query = "UPDATE guild_settings SET " \
                "created_voice_channel_ids = array_remove(created_voice_channel_ids, $2) " \
                "WHERE guild_id = $1"
        await self.pool.execute(query, member.guild.id, before.channel.id)
        self.created_channels_ids.remove(before.channel.id)

        await before.channel.delete()
        return

    async def load_settings(self, guild_id):
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
        else:
            self.created_channels_ids = []

    @commands.Cog.listener()
    async def on_voice_state_update(
            self, member: disnake.Member, before: disnake.VoiceState, current: disnake.VoiceState
    ):
        if before.channel == current.channel:
            return

        guild_id = member.guild.id
        await self.load_settings(guild_id)
        if current.channel and current.channel.id == self.channel_creator_id:
            print(f"{member} joined in create channel")
            await self.create_voice_channel(member)

        if before.channel and before.channel.category.id == self.category_id:
            if before.channel.id in self.created_channels_ids and not before.channel.members:
                await self.delete_voice_channel(member, before)

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
