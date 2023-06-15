import disnake
from disnake.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

class UserInteraction(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot



    @commands.slash_command()
    async def event_members(self, ctx: disnake.CommandInteraction):
        """Оповестить всех, кто находится в голосовом канале с Вами"""
        voice_channel_id = ctx.author.voice.channel.id
        voice_channel = self.bot.get_channel(voice_channel_id)
        members = voice_channel.members
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
        )
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(UserInteraction(bot))




