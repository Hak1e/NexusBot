import disnake
from disnake.ext import commands
from typing import Optional
import os
from dotenv import load_dotenv
import asyncpg
from core.bot import Nexus

load_dotenv()
emoji_like = os.getenv("EMOJI_LIKE")
emoji_dislike = os.getenv("EMOJI_DISLIKE")


# TODO: при отправке сообщения бот должен скинуть прикреплённую картинку в архив, скопировать её ссылку и уже потом отправить


async def send_embed(
        ctx: disnake.CommandInteraction,
        bot: commands.InteractionBot,
        image: disnake.Attachment,
        description: str,
        channel_id,
        title: str = None
):
    channel = bot.get_channel(channel_id)

    if channel is None:
        await ctx.send("Не удалось найти канал для отправки. Запустите команду `/setup`")
        return

    embed = (
        disnake.Embed(
            title=title if title else None,
            description=description,
            color=0x3f8fdf
        )
        .set_footer(text="Для доступа к каналу напишите machuku")
        .set_image(image)
    )
    message = await channel.send(embed=embed)
    await message.add_reaction(emoji=emoji_like)
    await message.add_reaction(emoji=emoji_dislike)
    await ctx.send("Сообщение успешно отправлено")


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
    async def say(
            self,
            ctx: disnake.CommandInteraction,
            message: str,
            channel: Optional[disnake.TextChannel] = None
    ):
        """Написать сообщение от лица бота"""

        channel = channel or ctx.channel

        await channel.send(message)

        await ctx.send("Сообщение отправлено", ephemeral=True)

    @commands.slash_command()
    async def art(
            self,
            ctx: disnake.CommandInteraction,
            image: disnake.Attachment,
            comment: Optional[str] = None,
            author: Optional[str] = None
    ):
        """Выложить арт

        Parameters
        ----------
        ctx: command interaction
        image: Добавить изображение
        comment: Комментарий к арту
        author: Указать автора, если это не Вы
        """

        async with self.pool.acquire() as conn:
            query = "SELECT art_channel_id FROM guild_settings WHERE guild_id = $1"
            self.art_channel_id = await conn.fetchval(query, ctx.guild.id)

        if author:
            description = f"**Автор:** {author}"
        else:
            description = f"**Автор:** {ctx.author.mention} ({ctx.author})"
        if comment:
            description += f"\n**Комментарий: **{comment}"
        await send_embed(
            ctx=ctx,
            bot=self.bot,
            title="Новый арт!",
            image=image,
            description=description,
            channel_id=self.art_channel_id
        )

    @commands.slash_command()
    async def meme(
            self,
            ctx: disnake.CommandInteraction,
            image: disnake.Attachment,
            author: Optional[str] = None,
    ):
        """Выложить мем

        Parameters
        ----------
        ctx: command interaction
        image: Добавить изображение
        author: Указать автора, если это не Вы
        """

        async with self.pool.acquire() as conn:
            query = "SELECT meme_channel_id FROM guild_settings WHERE guild_id = $1"
            self.meme_channel_id = await conn.fetchval(query, ctx.guild.id)

        if author:
            description = f"**Автор:** {author}"
        else:
            description = f"**Автор:** {ctx.author.mention} ({ctx.author})"
        await send_embed(
            ctx=ctx,
            bot=self.bot,
            image=image,
            description=description,
            channel_id=self.meme_channel_id
        )


class PingMembersInVoice(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command()
    async def event_members(
            self,
            ctx: disnake.CommandInteraction,
            bounty: int = None
    ):
        """Оповестить всех, кто находится в голосовом канале с Вами

        Parameters
        ----------
        ctx: command interactions
        bounty: валюта сервера
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
    bot.add_cog(PingMembersInVoice(bot))
