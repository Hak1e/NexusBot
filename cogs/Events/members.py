import disnake
from disnake.ext import commands
import asyncpg
import datetime


class Members(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = self.bot.get_pool()

    async def get_goodbye_channel(self, member):
        query = ("SELECT goodbye_channel_id "
                 "FROM text_channels "
                 "WHERE guild_id = $1")
        channel_id = await self.pool.fetchval(query, member.guild.id)
        if channel_id:
            channel = member.guild.get_channel(channel_id)
            return channel
        else:
            return None

    @commands.Cog.listener()
    async def on_member_remove(self, member: disnake.Member):
        channel = await self.get_goodbye_channel(member)
        if channel is None:
            return

        embed = disnake.Embed(title="🚪 Пользователь ушел", color=disnake.Color.red(),
                              description=f"**Пользователь:** `{member.name} ({member.id})`\n"
                                          f"**Всего пользователей:** `{len(member.guild.members)}`")
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)

        await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(Members(bot))
