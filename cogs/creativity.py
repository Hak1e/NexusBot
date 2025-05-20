import discord
from discord.ext import commands
from typing import Optional
from core.bot import Nexus
from models.errors import DataBaseFetchError


async def send_embed(
    ctx: discord.ApplicationContext,
    bot: commands.Bot,
    image_url,
    description,
    channel_id,
    reply_message,
    like,
    dislike,
    pool,
    title=None,
):
    channel = bot.get_channel(channel_id)

    if channel is None:
        await ctx.respond("Не удалось найти канал для отправки", ephemeral=True)
        return

    query = "SELECT text " "FROM creativity_footer_text " "WHERE guild_id = $1"
    footer_text = await pool.fetchval(query, ctx.guild.id)
    embed = (
        discord.Embed(
            title=title if title else None, description=description, color=0x3F8FDF
        )
        .set_footer(text=footer_text if footer_text else "")
        .set_image(url=image_url)
    )
    message = await channel.send(embed=embed)
    await message.add_reaction(emoji=like)
    await message.add_reaction(emoji=dislike)
    await ctx.respond(reply_message, ephemeral=True)


class Creativity(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool = bot.get_pool()

    async def load_emoji_reactions(self, ctx):
        query = "SELECT _like, dislike " "FROM emoji_reaction " "WHERE guild_id = $1"
        result = await self.pool.fetch(query, ctx.guild.id)
        if not result:
            return await ctx.respond("Ошибка загрузки реакций", ephemeral=True)
        like, dislike = result[0]["_like"], result[0]["dislike"]
        return like, dislike

    @commands.slash_command()
    async def art(
        self,
        ctx: discord.ApplicationContext,
        image_url: str,
        author: Optional[str] = None,
        comment: Optional[str] = None,
    ):
        """Выложить арт

        Parameters
        ----------
        ctx: command interaction
        image_url: Указать ссылку на изображение
        author: Указать автора, если это не Вы
        comment: Комментарий к арту
        """

        query = "SELECT id " "FROM art_channel " "WHERE guild_id = $1"
        art_channel_id = await self.pool.fetchval(query, ctx.guild.id)
        if not art_channel_id:
            await ctx.respond("Не найден канал для артов", ephemeral=True)
            raise DataBaseFetchError()
        like, dislike = await self.load_emoji_reactions(ctx)
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
            image_url=image_url,
            description=description,
            channel_id=art_channel_id,
            reply_message="Арт успешно опубликован",
            like=like,
            dislike=dislike,
            pool=self.pool,
        )

    @commands.slash_command()
    async def meme(
        self,
        ctx: discord.ApplicationContext,
        image_url: str,
        author: Optional[str] = None,
        comment: Optional[str] = None,
    ):
        """Выложить мем

        Parameters
        ----------
        ctx: command interaction
        image_url: Добавить изображение
        author: Указать автора, если это не Вы
        comment: Комментарий к мему
        """

        query = "SELECT id " "FROM meme_channel " "WHERE guild_id = $1"
        meme_channel_id = await self.pool.fetchval(query, ctx.guild.id)
        if not meme_channel_id:
            await ctx.respond("Не найден канал для мемов", ephemeral=True)
            raise DataBaseFetchError()

        like, dislike = await self.load_emoji_reactions(ctx)
        if author:
            description = f"**Автор:** {author}"
        else:
            description = f"**Автор:** {ctx.author.mention} ({ctx.author})"
        if comment:
            description += f"\n**Комментарий: **{comment}"
        await send_embed(
            ctx=ctx,
            bot=self.bot,
            image_url=image_url,
            description=description,
            channel_id=meme_channel_id,
            reply_message="Мем успешно опубликован",
            like=like,
            dislike=dislike,
            pool=self.pool,
        )


def setup(bot):
    bot.add_cog(Creativity(bot))
