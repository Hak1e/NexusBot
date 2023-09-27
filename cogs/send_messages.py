import disnake
from disnake.ext import commands
from typing import Optional
import asyncpg
from core.bot import Nexus


class SendMessages(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool = bot.get_pool()
        self.art_channel_id = None
        self.meme_channel_id = None

    @commands.slash_command()
    async def ping(self, ctx: disnake.CommandInteraction):
        """Проверить, находится ли бот в сети"""
        await ctx.send("Pong!")

    @commands.slash_command()
    async def say(self, ctx: disnake.CommandInteraction,
                  message: str, channel: Optional[disnake.TextChannel] = None):
        """Написать сообщение от лица бота"""
        channel = channel or ctx.channel
        await channel.send(message)
        await ctx.send("Сообщение отправлено", ephemeral=True)


def setup(bot):
    bot.add_cog(SendMessages(bot))
