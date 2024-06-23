import disnake
from disnake.ext import commands
from core.bot import Nexus
import asyncpg


class Punishments(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool: asyncpg.Pool = self.bot.get_pool()

    @commands.slash_command()
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx: disnake.CommandInteraction,
                   member: disnake.Member, reason=None):
        """Замьютить участника"""
        query = ("SELECT id "
                 "FROM guild_mute_role "
                 "WHERE guild_id = $1")
        muted_role_id = await self.pool.fetchval(query, ctx.guild.id)
        if muted_role_id is None:
            return await ctx.send("Роль мьюта не настроена на этом сервере. Обратитесь к администратору",
                                  ephemeral=True)
        muted_role = ctx.guild.get_role(muted_role_id)
        if not muted_role:
            return await ctx.send("Роль мьюта не найдена. Обратитесь к администратору", ephemeral=True)
        await member.add_roles(muted_role, reason=reason)
        await ctx.send(f"{member.mention} замьючен", ephemeral=True)

    @commands.slash_command()
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx: disnake.CommandInteraction,
                     member: disnake.Member, reason=None):
        """Разамьютить участника"""
        query = ("SELECT id "
                 "FROM guild_mute_role "
                 "WHERE guild_id = $1")
        muted_role_id = await self.pool.fetchval(query, ctx.guild.id)
        if muted_role_id is None:
            return await ctx.send("Роль мьюта не настроена на этом сервере. Обратитесь к администратору",
                                  ephemeral=True)
        muted_role = ctx.guild.get_role(muted_role_id)
        if not muted_role:
            return await ctx.send("Роль мьюта не найдена. Обратитесь к администратору", ephemeral=True)
        await member.remove_roles(muted_role, reason=reason)
        await ctx.send(f"{member.mention} разамьючен", ephemeral=True)


def setup(bot):
    bot.add_cog(Punishments(bot))
