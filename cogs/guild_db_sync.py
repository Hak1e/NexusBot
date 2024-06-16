import disnake
from disnake.ext import commands


class GuildSync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = bot.get_pool()

    @commands.slash_command()
    async def restore(self, ctx):
        """Настройка синхронизации ролей и никнеймов участников сервера"""
        pass

    @restore.sub_command_group()
    async def member(self, ctx):
        pass

    @member.sub_command()
    async def roles(self, ctx: disnake.CmdInter,
                    value: bool):
        """Включить/отключить восстановление ролей для перезашедших участников

        Parameters
        ----------
        ctx: command interaction
        value: Будут ли сохраняться данные
        """
        if value:
            query = ("UPDATE guild_sync "
                     "SET member_roles = TRUE "
                     "WHERE guild_id = $1")
            await self.pool.execute(query, ctx.guild.id)
            return await ctx.send("Восстановление ролей для перезашедших участников включено", ephemeral=True)

        else:
            query = ("UPDATE guild_sync "
                     "SET member_roles = FALSE "
                     "WHERE guild_id = $1")
            await self.pool.execute(query, ctx.guild.id)
            return await ctx.send("Восстановление ролей для перезашедших участников отключено", ephemeral=True)

    @member.sub_command()
    async def name(self, ctx: disnake.CmdInter,
                   value: bool):
        """Включить/отключить восстановление никнейма для перезашедших участников

        Parameters
        ----------
        ctx: command interaction
        value: Будут ли сохраняться данные
        """
        if value:
            query = ("UPDATE guild_sync "
                     "SET member_name = TRUE "
                     "WHERE guild_id = $1")
            await self.pool.execute(query, ctx.guild.id)
            return await ctx.send("Восстановление никнейма для перезашедших участников включено", ephemeral=True)
        else:
            query = ("UPDATE guild_sync "
                     "SET member_name = FALSE "
                     "WHERE guild_id = $1")
            await self.pool.execute(query, ctx.guild.id)
            return await ctx.send("Восстановление никнейма для перезашедших участников отключено", ephemeral=True)


def setup(bot):
    bot.add_cog(GuildSync(bot))
