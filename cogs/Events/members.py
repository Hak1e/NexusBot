import disnake
from disnake.ext import commands
import asyncpg
import datetime


class Members(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = self.bot.get_pool()

    async def get_goodbye_channel(self, member):
        query = ("SELECT id "
                 "FROM goodbye_channel "
                 "WHERE guild_id = $1")
        channel_id = await self.pool.fetchval(query, member.guild.id)
        if channel_id:
            channel = member.guild.get_channel(channel_id)
            return channel
        else:
            return None

    async def get_sync_settings(self, guild_id):
        query = ("SELECT member_name, member_roles "
                 "FROM guild_sync "
                 "WHERE guild_id = $1")
        sync_settings = await self.pool.fetchrow(query, guild_id)
        sync_member_name = sync_settings["member_name"]
        sync_member_roles = sync_settings["member_roles"]
        return sync_member_name, sync_member_roles

    @commands.Cog.listener()
    async def on_member_remove(self, member: disnake.Member):
        sync_member_name, sync_member_roles = await self.get_sync_settings(member.guild.id)
        if sync_member_name:
            query = ("INSERT INTO guild_member (id, guild_id, nick) "
                     "VALUES ($1, $2, $3) "
                     "ON CONFLICT (id, nick) DO UPDATE "
                     "SET nick = $3")
            await self.pool.execute(query, member.id,
                                    member.guild.id, member.name)
        if sync_member_roles:
            member_roles = member.roles
            member_roles_ids = [role.id for role in member_roles]
            query = ("DELETE FROM member_role "
                     "WHERE member_id = $1 and guild_id = $2")
            await self.pool.execute(query, member.id,
                                    member.guild.id)
            for role_id in member_roles_ids:
                query = ("INSERT INTO member_role (member_id, guild_id, role_id) "
                         "VALUES ($1, $2, $3)")
                await self.pool.execute(query, member.id,
                                        member.guild.id, role_id)

        channel = await self.get_goodbye_channel(member)
        if channel is None:
            return

        embed = disnake.Embed(title="🚪 Пользователь ушел", color=disnake.Color.red(),
                              description=f"**Пользователь:** `{member.name} ({member.id})`\n"
                                          f"**Всего пользователей:** `{len(member.guild.members)}`")
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        sync_member_name, sync_member_roles = await self.get_sync_settings(member.guild.id)
        if sync_member_name:
            query = ("SELECT nick "
                     "FROM guild_member "
                     "WHERE id = $1 and guild_id = $2")
            nick = await self.pool.fetchval(query, member.id,
                                            member.guild.id)
            if nick:
                await member.edit(nick=nick)
        if sync_member_roles:
            query = ("SELECT role_id "
                     "FROM member_role "
                     "WHERE member_id = $1 and guild_id = $2")
            member_roles_ids = await self.pool.fetch(query, member.id,
                                                     member.guild.id)
            if member_roles_ids:
                member_roles_ids = [role_id["role_id"] for role_id in member_roles_ids]
                member_roles = [member.guild.get_role(role_id) for role_id in member_roles_ids]
                await member.add_roles(*member_roles)

    @commands.Cog.listener()
    async def on_member_update(self, old_member_info: disnake.Member,
                               current_member_info: disnake.Member):
        # nickname, roles
        pass


def setup(bot):
    bot.add_cog(Members(bot))
