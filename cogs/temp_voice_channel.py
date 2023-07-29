import disnake
from disnake.ext import commands
import asyncpg
from core.bot import Nexus
import asyncio


class OnJoinChannel(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool: asyncpg.Pool = bot.get_pool()
        self.category_id = None
        self.channel_creator_id = None
        self.channel_author_id = None
        self.custom_channel_name = None

    async def create_voice_channel(self, member: disnake.Member):
        query = "SELECT channel_name " \
                "FROM custom_voice " \
                "WHERE guild_id = $1 and user_id = $2"
        self.custom_channel_name = await self.pool.fetchval(query, member.guild.id, member.id)

        category = member.guild.get_channel(self.category_id)
        channel_name = self.custom_channel_name or f"{member.name}'s channel"

        voice_channel = await member.guild.create_voice_channel(
            name=channel_name, category=category, overwrites=category.overwrites
        )
        query = "INSERT INTO custom_voice (guild_id, user_id, channel_id)" \
                "VALUES ($1, $2, $3)" \
                "ON CONFLICT (guild_id, user_id) DO UPDATE " \
                "SET channel_id = $3"
        await self.pool.execute(query, member.guild.id, member.id, voice_channel.id)
        category_ow = category.overwrites
        await asyncio.sleep(0.7)  # без этого права пользователю могут не добавиться
        # Значение 0.7 - минимальное для корректной работы

        if member in category_ow:
            category_ow[member].update(
                view_channel=True, manage_channels=True, manage_permissions=True, move_members=True)
            await voice_channel.edit(overwrites=category_ow)
        else:
            await voice_channel.set_permissions(
                member, view_channel=True, manage_channels=True, manage_permissions=True, move_members=True)

        try:
            await member.move_to(voice_channel)
        except disnake.errors.HTTPException:
            await self.delete_voice_channel(member, voice_channel)

        return

    async def delete_voice_channel(self, member: disnake.Member, channel: disnake.VoiceChannel):
        query = "SELECT user_id " \
                "FROM custom_voice " \
                "WHERE guild_id = $1 and channel_id = $2"
        self.channel_author_id = await self.pool.fetchval(query, member.guild.id, channel.id)

        query = "INSERT INTO custom_voice (guild_id, user_id, channel_id, channel_name)" \
                "VALUES ($1, $2, $3, $4)" \
                "ON CONFLICT (guild_id, user_id) DO UPDATE " \
                "SET channel_id = $3, channel_name = $4"
        await self.pool.execute(query, member.guild.id, self.channel_author_id, None, channel.name)

        self.channel_author_id = None
        await channel.delete()
        return

    @commands.Cog.listener()
    async def on_voice_state_update(
            self, member: disnake.Member, before: disnake.VoiceState, current: disnake.VoiceState
    ):
        if before.channel == current.channel:
            return

        guild_id = member.guild.id
        query = "SELECT voice_channel_category_id, channel_creator_id " \
                "FROM guild_settings " \
                "WHERE guild_id = $1"
        try:
            self.category_id, self.channel_creator_id = await self.pool.fetchrow(query, guild_id)
        except TypeError:
            return

        if before.channel and before.channel.category.id == self.category_id\
                and before.channel.id != self.channel_creator_id\
                and not before.channel.members:
            await self.delete_voice_channel(member, before.channel)

        if current.channel and current.channel.id == self.channel_creator_id:
            await self.create_voice_channel(member)



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
        # await self.pool.execute(query, member_or_id.id, self.custom_channel_name, self.permissions)


def setup(bot):
    bot.add_cog(OnJoinChannel(bot))
