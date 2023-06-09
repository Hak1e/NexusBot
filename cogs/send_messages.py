import disnake
from disnake.ext import commands
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()
art_channel_id = int(os.getenv("ART_CHANNEL_ID"))  # RU HOTS, Искусство
artist_role_id = int(os.getenv("ARTIST_ROLE_ID"))  # RU HOTS, Художник
humor_channel_id = int(os.getenv("HUMOR_CHANNEL_ID"))  # RU HOTS, Юмор
humorist_role_id = int(os.getenv("HUMORIST_ROLE_ID"))  # RU HOTS, Юморист
emoji_like = os.getenv("EMOJI_LIKE")
emoji_dislike = os.getenv("EMOJI_DISLIKE")


async def send_embed(
        ctx: disnake.CommandInteraction,
        bot: commands.Bot,
        image: disnake.Attachment,
        description: str,
        channel_id,
        title: str = None
):
    channel = bot.get_channel(channel_id)
    embed = (
        disnake.Embed(
            title=title if title else None,
            description=description,
            color=0x3f8fdf
        )
        .set_footer(text="Для доступа к каналу напишите MACHUKU")
        .set_image(image)
    )
    message = await channel.send(embed=embed)
    await message.add_reaction(emoji=emoji_like)
    await message.add_reaction(emoji=emoji_dislike)



class SendMessages(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @commands.slash_command()
    async def say(
            self,
            ctx: disnake.CommandInteraction,
            message: str,
            channel: Optional[disnake.TextChannel] = None
    ):
        """Write message from bot"""
        channel = channel or ctx.channel
        await channel.send(message)

        await ctx.send("Message sent", ephemeral=True)


    @commands.slash_command()
    async def art(
            self,
            ctx: disnake.CommandInteraction,
            image: disnake.Attachment,
            comment: Optional[str] = None,
            author: Optional[str] = None,
    ):
        """Выложить арт

        Parameters
        ----------
        ctx: command interaction
        image: Добавить изображение
        comment: Комментарий к арту
        author: Указать автора, если это не Вы
        """
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
            channel_id=art_channel_id
        )
        await ctx.send("Арт успешно опубликован!")

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
        if author:
            description = f"**Автор:** {author}"
        else:
            description = f"**Автор:** {ctx.author.mention} ({ctx.author})"
        await send_embed(
            ctx=ctx,
            bot=self.bot,
            image=image,
            description=description,
            channel_id=humor_channel_id
        )
        await ctx.send("Мем успешно опубликован!")


def setup(bot):
    bot.add_cog(SendMessages(bot))