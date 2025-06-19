import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands


class GuildSync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = bot.get_pool()

    restore = SlashCommandGroup(
        "restore", "Настройка синхронизации ролей и никнеймов участников сервера"
    )

    member = restore.create_subgroup("member")

    @member.command()
    async def roles(self, ctx: discord.ApplicationContext, value: bool):
        """Включить/отключить восстановление ролей для перезашедших участников

        Parameters
        ----------
        ctx: command interaction
        value: Будут ли сохраняться данные
        """
        if value:
            query = "UPDATE guild_sync SET member_roles = TRUE WHERE guild_id = $1"
            await self.pool.execute(query, ctx.guild.id)
            return await ctx.respond(
                "Восстановление ролей для перезашедших участников включено",
                ephemeral=True,
            )

        else:
            query = "UPDATE guild_sync SET member_roles = FALSE WHERE guild_id = $1"
            await self.pool.execute(query, ctx.guild.id)
            return await ctx.respond(
                "Восстановление ролей для перезашедших участников отключено",
                ephemeral=True,
            )

    @member.command()
    async def name(self, ctx: discord.ApplicationContext, value: bool):
        """Включить/отключить восстановление никнейма для перезашедших участников

        Parameters
        ----------
        ctx: command interaction
        value: Будут ли сохраняться данные
        """
        if value:
            query = "UPDATE guild_sync SET member_name = TRUE WHERE guild_id = $1"
            await self.pool.execute(query, ctx.guild.id)
            return await ctx.respond(
                "Восстановление никнейма для перезашедших участников включено",
                ephemeral=True,
            )
        else:
            query = "UPDATE guild_sync SET member_name = FALSE WHERE guild_id = $1"
            await self.pool.execute(query, ctx.guild.id)
            return await ctx.respond(
                "Восстановление никнейма для перезашедших участников отключено",
                ephemeral=True,
            )


def setup(bot):
    bot.add_cog(GuildSync(bot))
