import disnake
from disnake.ext import commands
from typing import Optional
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

    async def wait_for_message(self, ctx):
        def check(msg):
            return msg.author.id == ctx.author.id and msg.channel == ctx.channel

        return await self.bot.wait_for("message", check=check)

    @commands.slash_command()
    async def echo(self, ctx: disnake.CommandInteraction,
                   channel_id, guild_id=None):
        """Начать слушать сообщения пользователя и отправлять их в указанный чат

        Parameters
        ----------
        ctx: command interaction
        channel_id: Указать ID канала для отправки сообщения
        guild_id: Указать ID сервера. Указывать, если канал на другом сервере
        """
        accepted_person_ids = [389787190986670082, 434780487127400459]
        if ctx.author.id not in accepted_person_ids:
            await ctx.send("Вам не разрешено использовать данную команду", ephemeral=True)
            return

        try:
            guild = ctx.bot.get_guild(int(guild_id)) if guild_id else ctx.guild
            if not guild:
                raise ValueError
        except:
            await ctx.send("Не найден указанный сервер", ephemeral=True)
            return
        try:
            channel = guild.get_channel(int(channel_id))
            if not channel:
                raise ValueError
        except:
            await ctx.send("Не найден канал на этом сервере", ephemeral=True)
            return

        await ctx.send("Начните вводить сообщения, которые будут отправлены в указанный канал\n"
                       "Чтобы остановить команду, введите `<<stop`", ephemeral=True)
        while True:
            message = await self.wait_for_message(ctx)
            if message.content == "<<stop":
                await message.delete()
                await ctx.send("Отправка сообщений остановлена", ephemeral=True)
                break

            if message.attachments:
                attachments = [await attachment.to_file() for attachment in message.attachments]
                await channel.send(message.content, files=attachments)
            else:
                await channel.send(message.content)
            await message.delete()


def setup(bot):
    bot.add_cog(SendMessages(bot))
