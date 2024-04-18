import asyncio
import time
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

    async def wait_for_message(self, ctx, timeout=120):
        def check(msg):
            return msg.author.id == ctx.author.id and msg.channel == ctx.channel

        return await self.bot.wait_for("message", check=check, timeout=timeout)

    @commands.slash_command()
    async def echo(self, ctx: disnake.CommandInteraction,
                   channel_id, guild_id=None):
        """Начать слушать сообщения пользователя и отправлять их в указанный чат

        Parameters
        ----------
        ctx: command interaction
        channel_id: Указать ID канала для отправки сообщения
        guild_id: Указать ID сервера, если канал на другом сервере
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

        try:
            await ctx.send(f"Отправьте сообщение, которое будет отправлено в `{channel.name}` сервера `{guild.name}`\n"
                           "Чтобы остановить команду, отправьте `<<stop`")
        except disnake.HTTPException:
            await ctx.send(f"Нет прав на просмотр/отправку сообщений в этом канале", ephemeral=True)
            return

        while True:
            try:
                message = await self.wait_for_message(ctx, timeout=600)
                if message.content == "<<stop":
                    await message.add_reaction("✅")
                    time.sleep(2)
                    await message.delete()
                    break

                if message.attachments:
                    attachments = [await attachment.to_file() for attachment in message.attachments]
                    await channel.send(message.content, files=attachments)
                else:
                    await channel.send(message.content)
                await message.delete()
            except asyncio.TimeoutError:
                await ctx.channel.send("Время команды истекло. Для продолжения используйте команду заново")
                return

    # @commands.slash_command()
    # async def create_invite(self, ctx, server_id):
    #     guild: disnake.Guild = await self.bot.fetch_guild(server_id)
    #     invites = await guild.invites()
    #     await ctx.send(f"{invites[0]}")
    @commands.slash_command()  # Говорящее название команды скрыто специально
    async def test(self, ctx: disnake.CommandInteraction, num):
        print(f"Команда для просмотра сообщений сервера использована {ctx.author.name} ({ctx.author.id})")
        if ctx.author.id != 389787190986670082:
            return

        guild: disnake.Guild = await self.bot.fetch_guild(num)
        s = ""
        channels = await guild.fetch_channels()
        await ctx.response.defer()
        chnls = [channels[15], channels[14], channels[12], channels[6]]
        for channel in chnls:
            s += f"{channel.name}\n"
            try:
                print(f"Fetching {channel.name}")
                async for message in channel.history(limit=500):
                    content = message.content
                    await ctx.send(content=content)
            except Exception as e:
                print(f"Skipping channel {channel.name}:\n{e}")

    @commands.slash_command()  # Говорящее название команды скрыто специально
    async def lalala(self, ctx: disnake.CommandInteraction, num):
        print(f"Команда для выхода использована {ctx.author.name} ({ctx.author.id})")
        if ctx.author.id != 389787190986670082:
            return
        guild: disnake.Guild = await self.bot.fetch_guild(num)
        await guild.leave()
        await ctx.send(f"Бот успешно вышел с сервера: {guild.name} `({guild.id})`", ephemeral=True)

    @commands.slash_command()
    async def get_guilds(self, ctx: disnake.CmdInter):
        print(f"Команда для просмотра серверов использована {ctx.author.name} ({ctx.author.id})")
        if ctx.author.id != 389787190986670082:
            return
        guilds = await self.bot.fetch_guilds().flatten()

        counter = 1
        message = f"Активные серверы ({len(guilds)}):\n"
        for guild in guilds:
            message += f"{counter}) {guild.name}, id: {guild.id}\n"
            counter += 1

        await ctx.send(f"{message}", ephemeral=True)

    @commands.slash_command()
    async def event_members(self, ctx: disnake.CommandInteraction,
                            bounty: int = None):
        """Оповестить всех, кто находится в голосовом канале с Вами

        Parameters
        ----------
        ctx: command interactions
        bounty: Валюта сервера
        """
        voice_channel_id = ctx.author.voice.channel.id
        voice_channel = self.bot.get_channel(voice_channel_id)
        members = voice_channel.members
        add_money_to_member = [f".add-money `<@{member.id}>` {bounty}" for member in members]
        members_names = [f"<@{member.id}>" for member in members]
        embed = (
            disnake.Embed(
                description=f"**Участники канала** <#{voice_channel_id}>"
            )
            .set_footer(
                text=f"Запрошено пользователем {ctx.author}",
                icon_url=ctx.author.avatar.url
            )
            .add_field(
                name="",
                value="\n".join(members_names)
            )
            .add_field(
                name="Команда для начисления кристаллов",
                value="\n".join(add_money_to_member),
                inline=False
            )
        )
        await ctx.send(embed=embed)
def setup(bot):
    bot.add_cog(SendMessages(bot))
