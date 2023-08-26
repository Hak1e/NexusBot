import disnake
from disnake.ext import commands
from typing import Optional
import asyncpg
from core.bot import Nexus


async def send_embed(ctx: disnake.CommandInteraction, bot: commands.InteractionBot,
                     image_url, description,
                     channel_id, reply_message,
                     like, dislike,
                     title=None):
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
        .set_image(url=image_url)
    )
    message = await channel.send(embed=embed)
    await message.add_reaction(emoji=like)
    await message.add_reaction(emoji=dislike)
    await ctx.send(reply_message)


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

    async def load_emoji_reactions(self, ctx):
        query = "SELECT _like, _dislike " \
                "FROM emoji_reactions " \
                "WHERE guild_id = $1"
        result = await self.pool.fetch(query, ctx.guild.id)
        like, dislike = result[0]["_like"], result[0]["_dislike"]
        return like, dislike

    @commands.slash_command()
    async def art(self, ctx: disnake.CommandInteraction,
                  image_url: str, comment: Optional[str] = None,
                  author: Optional[str] = None):
        """Выложить арт

        Parameters
        ----------
        ctx: command interaction
        image_url: Указать ссылку на изображение
        comment: Комментарий к арту
        author: Указать автора, если это не Вы
        """

        query = "SELECT art_channel_id " \
                "FROM text_channels " \
                "WHERE guild_id = $1"
        self.art_channel_id = await self.pool.fetchval(query, ctx.guild.id)

        like, dislike = await self.load_emoji_reactions(ctx)
        if author:
            description = f"**Автор:** {author}"
        else:
            description = f"**Автор:** {ctx.author.mention} ({ctx.author})"
        if comment:
            description += f"\n**Комментарий: **{comment}"
        await send_embed(ctx=ctx, bot=self.bot,
                         title="Новый арт!", image_url=image_url,
                         description=description, channel_id=self.art_channel_id,
                         reply_message="Арт успешно опубликован", like=like,
                         dislike=dislike)

    @commands.slash_command()
    async def meme(self, ctx: disnake.CommandInteraction,
                   image_url: str, author: Optional[str] = None):
        """Выложить мем

        Parameters
        ----------
        ctx: command interaction
        image_url: Добавить изображение
        author: Указать автора, если это не Вы
        """

        query = "SELECT meme_channel_id FROM text_channels WHERE guild_id = $1"
        self.meme_channel_id = await self.pool.fetchval(query, ctx.guild.id)

        like, dislike = await self.load_emoji_reactions(ctx)
        if author:
            description = f"**Автор:** {author}"
        else:
            description = f"**Автор:** {ctx.author.mention} ({ctx.author})"
        await send_embed(ctx=ctx, bot=self.bot,
                         image_url=image_url,
                         description=description, channel_id=self.meme_channel_id,
                         reply_message="Мем успешно опубликован", like=like,
                         dislike=dislike)


def setup(bot):
    bot.add_cog(SendMessages(bot))
