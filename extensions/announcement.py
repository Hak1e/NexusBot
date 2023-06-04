import hikari
import lightbulb
from dotenv import load_dotenv
import os
from typing import Optional


load_dotenv()

announcement_plugin = lightbulb.Plugin("Announcement")

art_channel_id = int(os.getenv("ART_CHANNEL_ID"))  # RU HOTS, Искусство
artist_id = int(os.getenv("ARTIST_ROLE_ID"))  # RU HOTS, Художник
humor_channel_id = int(os.getenv("HUMOR_CHANNEL_ID"))  # RU HOTS, Юмор
humorist_id = int(os.getenv("HUMORIST_ROLE_ID"))  # RU HOTS, Юморист

emoji_like = os.getenv("EMOJI_LIKE")
emoji_dislike = os.getenv("EMOJI_DISLIKE")

emoji_like_name = emoji_like[1:len(emoji_like) - 1:].split(":")[1]
emoji_like_id = emoji_like[1:len(emoji_like) - 1:].split(":")[2]

emoji_dislike_name = emoji_dislike[1:len(emoji_dislike) - 1:].split(":")[1]
emoji_dislike_id = emoji_dislike[1:len(emoji_dislike) - 1:].split(":")[2]


async def send_embed(
        ctx: lightbulb.SlashContext,
        image: hikari.Attachment,
        description: str,
        channel_id,
        title: str = None
):
    channel = announcement_plugin.bot.cache.get_guild_channel(channel_id)
    embed = (
        hikari.Embed(
            title=title if title else None,
            description=description,
            color=0x3f8fdf
        )
        .set_footer("Для доступа к каналу напишите MACHUKU")
        .set_image(image)
    )

    message = await channel.send(embed=embed)
    await message.add_reaction(emoji=emoji_like_name, emoji_id=emoji_like_id)
    await message.add_reaction(emoji=emoji_dislike_name, emoji_id=emoji_dislike_id)


@announcement_plugin.command
@lightbulb.option("image", "Добавить изображение к сообщению", type=hikari.Attachment)
@lightbulb.option("comment", "Комментарий к арту", required=False)
@lightbulb.option("author", "Указать ДРУГОГО автора", required=False)
@lightbulb.command("art", "Выложить арт", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def art(
        ctx: lightbulb.SlashContext,
        image: hikari.Attachment,
        comment: Optional[str] = None,
        author: Optional[str] = None
) -> None:
    if author:
        description = f"**Автор:** {author}"
    else:
        description = f"**Автор:** {ctx.author.mention} ({ctx.author})"
    if comment:
        description += f"\n{comment}"
    await send_embed(
        ctx=ctx,
        title="Новый арт!",
        image=image, description=description,
        channel_id=art_channel_id
    )
    await ctx.respond(f"Арт успешно опубликован!")


@announcement_plugin.command
@lightbulb.option("image", "Добавить изображение к сообщению", type=hikari.Attachment)
@lightbulb.option("author", "Указать ДРУГОГО автора", required=False)
@lightbulb.command("meme", "Выложить мем", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def meme(
        ctx: lightbulb.SlashContext,
        image: hikari.Attachment,
        author: Optional[str] = None
) -> None:
    if author:
        description = f"**Автор:** {author}"
    else:
        description = f"**Автор:** {ctx.author.mention} ({ctx.author})"
    await send_embed(
        ctx=ctx,
        image=image,
        description=description,
        channel_id=humor_channel_id
    )
    await ctx.respond(f"Мем успешно опубликован!")


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(announcement_plugin)

