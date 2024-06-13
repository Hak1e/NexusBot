import disnake
from disnake.ext import commands
from core.bot import Nexus
import asyncpg


class Punishments(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool: asyncpg.Pool = self.bot.get_pool()


    #@commands.slash_command()
    async def mute(self, ctx: disnake.CommandInteraction, member: disnake.Member):
        """Замьютить участника"""
        query = ("SELECT role_id "
                 "FROM muted_role "
                 "WHERE guild_id = $1")
        muted_role_id = await self.pool.fetchval(query, ctx.guild.id)
        if muted_role_id is None:
            await ctx.send(f"Роль мьюта не настроена на этом сервере. Обратитесь к администратору")
            return
        muted_role = ctx.guild.get_role(muted_role_id)



def setup(bot):
    bot.add_cog(Punishments(bot))
