import disnake
from disnake.ext import commands
from typing import Optional
from core.bot import Nexus
from models.errors import DataBaseFetchError


async def send_embed(ctx: disnake.CommandInteraction, bot: commands.InteractionBot,
                     image_url, description,
                     channel_id, reply_message,
                     like, dislike,
                     pool, title=None):
    channel = bot.get_channel(channel_id)

    if channel is None:
        await ctx.send("Не удалось найти канал для отправки", ephemeral=True)
        return

    query = ("SELECT text "
             "FROM creativity_footer_text "
             "WHERE guild_id = $1")
    footer_text = await pool.fetchval(query, ctx.guild.id)
    embed = (
        disnake.Embed(
            title=title if title else None,
            description=description,
            color=0x3f8fdf
        )
        .set_footer(text=footer_text if footer_text else "")
        .set_image(url=image_url)
    )
    message = await channel.send(embed=embed)
    await message.add_reaction(emoji=like)
    await message.add_reaction(emoji=dislike)
    await ctx.send(reply_message)


class Creativity(commands.Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.pool = bot.get_pool()

    async def load_emoji_reactions(self, ctx):
        query = "SELECT _like, _dislike " \
                "FROM emoji_reactions " \
                "WHERE guild_id = $1"
        result = await self.pool.fetch(query, ctx.guild.id)
        if result[0][0] and result[0][1]:
            like, dislike = result[0]["_like"], result[0]["_dislike"]
            return like, dislike
        else:
            error_message = "Ошибка загрузки реакций. Необходима настройка"
            await ctx.send(error_message, ephemeral=True)
            raise DataBaseFetchError(error_message)

    @commands.slash_command()
    async def art(self, ctx: disnake.CommandInteraction,
                  image_url: str, author: Optional[str] = None,
                  comment: Optional[str] = None):
        """Выложить арт

        Parameters
        ----------
        ctx: command interaction
        image_url: Указать ссылку на изображение
        author: Указать автора, если это не Вы
        comment: Комментарий к арту
        """

        query = "SELECT art_channel_id " \
                "FROM text_channels " \
                "WHERE guild_id = $1"
        art_channel_id = await self.pool.fetchval(query, ctx.guild.id)
        if not art_channel_id:
            await ctx.send("Не найден канал для артов", ephemeral=True)
            raise DataBaseFetchError()
        like, dislike = await self.load_emoji_reactions(ctx)
        if author:
            description = f"**Автор:** {author}"
        else:
            description = f"**Автор:** {ctx.author.mention} ({ctx.author})"
        if comment:
            description += f"\n**Комментарий: **{comment}"
        await send_embed(ctx=ctx, bot=self.bot,
                         title="Новый арт!", image_url=image_url,
                         description=description, channel_id=art_channel_id,
                         reply_message="Арт успешно опубликован", like=like,
                         dislike=dislike)

    @commands.slash_command()
    async def meme(self, ctx: disnake.CommandInteraction,
                   image_url: str, author: Optional[str] = None,
                   comment: Optional[str] = None):
        """Выложить мем

        Parameters
        ----------
        ctx: command interaction
        image_url: Добавить изображение
        author: Указать автора, если это не Вы
        comment: Комментарий к мему
        """

        query = "SELECT meme_channel_id FROM text_channels WHERE guild_id = $1"
        meme_channel_id = await self.pool.fetchval(query, ctx.guild.id)
        if not meme_channel_id:
            await ctx.send("Не найден канал для мемов", ephemeral=True)
            raise DataBaseFetchError()

        like, dislike = await self.load_emoji_reactions(ctx)
        if author:
            description = f"**Автор:** {author}"
        else:
            description = f"**Автор:** {ctx.author.mention} ({ctx.author})"
        if comment:
            description += f"\n**Комментарий: **{comment}"
        await send_embed(ctx=ctx, bot=self.bot,
                         image_url=image_url,
                         description=description, channel_id=meme_channel_id,
                         reply_message="Мем успешно опубликован", like=like,
                         dislike=dislike)


def setup(bot):
    bot.add_cog(Creativity(bot))
