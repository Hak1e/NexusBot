import disnake
from disnake.ext import commands
import asyncpg
from cogs.team_lobby import MembersSelectMenu
from cogs.team_lobby import ChannelActions
from models.lobby_settings import AuthorSettings, LobbyChannelSettings
from cogs.team_lobby import BaseDashboardButtons, CustomChannelDashboardButtons, generate_initial_embed_message


class ChannelCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = self.bot.get_pool()
        self.author_settings = AuthorSettings(bot)
        self.lobby_settings = LobbyChannelSettings(bot)

    async def is_channel_author(self, ctx):
        if await self.author_settings.get_voice_channel_author_id(ctx.channel) != ctx.author.id:
            await ctx.send("Вы можете использовать команды только в своём канале", ephemeral=True)
            return False
        return True

    @commands.slash_command(name="channel")
    async def voice_channel(self, ctx):
        """Команды для управления каналом вместо кнопок"""
        pass

    @voice_channel.sub_command()
    async def dashboard(self, ctx: disnake.CmdInter):
        """Открыть панель управления каналом"""
        if not isinstance(ctx.channel, disnake.VoiceChannel):
            return await ctx.send("Используйте команду в своём голосовом канале", ephemeral=True)
        if not await self.is_channel_author(ctx):
            return await ctx.send("Вы можете использовать команды только в своём канале", ephemeral=True)
        hello_embed = generate_initial_embed_message(ctx.author)
        if await self.lobby_settings.is_custom(ctx.channel.id):
            buttons = CustomChannelDashboardButtons(self.pool, self.bot)
            await ctx.channel.send(embed=hello_embed, view=buttons)
        else:
            buttons = BaseDashboardButtons(self.pool, self.bot)
            await ctx.channel.send(embed=hello_embed, view=buttons)
        await ctx.send("Сообщение создано", ephemeral=True)

    @voice_channel.sub_command(name="kick")
    async def vc_kick(self, ctx: disnake.CmdInter,
                      member: disnake.Member):
        """Выгнать участника из канала"""
        if not await self.is_channel_author(ctx):
            return await ctx.send("Вы можете использовать команды только в своём канале", ephemeral=True)
        if ctx.author.id == member.id:
            await ctx.send("Вы не можете выгнать самого себя", ephemeral=True)
            return
        if member in ctx.channel.members:
            await member.move_to(None)  # type: ignore
            await ctx.send(f"{member.mention} выгнан из комнаты", ephemeral=True)

    @voice_channel.sub_command(name="ban")
    async def vc_ban(self, ctx,
                     member: disnake.Member):
        """Заблокировать участника канале"""
        if not await self.is_channel_author(ctx):
            return await ctx.send("Вы можете использовать команды только в своём канале", ephemeral=True)
        if ctx.author.id == member.id:
            await ctx.send("Вы не можете забанить самого себя", ephemeral=True)
            return
        await ctx.channel.set_permissions(member, connect=False)
        await self.author_settings.update_voice_channel_overwrites(ctx.channel)
        await ctx.send(f"{member.mention} забанен в этом голосовом канале", ephemeral=True)
        if member in ctx.channel.members:
            await member.move_to(None)  # type: ignore

    @voice_channel.sub_command(name="unban")
    async def vc_unban(self, ctx):
        """Разблокировать участника канале"""
        if not await self.is_channel_author(ctx):
            return await ctx.send("Вы можете использовать команды только в своём канале", ephemeral=True)
        channel: disnake.VoiceChannel = ctx.channel  # type: ignore
        members = []
        for value, permission in channel.overwrites.items():
            if permission.connect is False:
                members.append(value)
        if not members:
            return await ctx.send("В настройках канала нет заблокированных участников", ephemeral=True)
        select_menu = MembersSelectMenu(members, self.pool,
                                        ChannelActions.unban)
        view = disnake.ui.View()
        view.add_item(select_menu)
        await ctx.send(view=view, ephemeral=True)

    @voice_channel.sub_command()
    async def visible(self, ctx,
                      value: bool):
        """Сменить видимость канала"""
        if not await self.is_channel_author(ctx):
            return await ctx.send("Вы можете использовать команды только в своём канале", ephemeral=True)
        default_role = ctx.guild.default_role
        value = None if value else False
        await ctx.channel.set_permissions(default_role, view_channel=value)
        assert isinstance(ctx.channel, disnake.VoiceChannel)
        await self.author_settings.update_voice_channel_overwrites(ctx.channel)
        await ctx.send("Комната скрыта" if value is True else "Комната больше не скрыта", ephemeral=True)

    @voice_channel.sub_command()
    async def connect(self, ctx,
                      value: bool):
        """Сменить разрешение на подключение к каналу"""
        if not await self.is_channel_author(ctx):
            return await ctx.send("Вы можете использовать команды только в своём канале", ephemeral=True)
        default_role = ctx.guild.default_role
        value = None if value else False
        await ctx.channel.set_permissions(default_role, connect=value)
        assert isinstance(ctx.channel, disnake.VoiceChannel)
        await self.author_settings.update_voice_channel_overwrites(ctx.channel)
        await ctx.send("Комната закрыта" if value is True else "Комната больше не закрыта", ephemeral=True)

    @voice_channel.sub_command()
    async def name(self, ctx,
                   value):
        """Изменить название канала"""
        if not await self.is_channel_author(ctx):
            return await ctx.send("Вы можете использовать команды только в своём канале", ephemeral=True)
        await ctx.channel.edit(name=value)
        await self.author_settings.update_voice_channel_name(ctx.channel)
        await ctx.send(embed=disnake.Embed(description=f"Название канала успешно изменено на: `{value}`",
                                           color=disnake.Color.green()), ephemeral=True)

    @voice_channel.sub_command()
    async def bitrate(self, ctx,
                      value):
        """Изменить битрейт канала"""
        if not await self.is_channel_author(ctx):
            return await ctx.send("Вы можете использовать команды только в своём канале", ephemeral=True)
        await ctx.channel.edit(bitrate=value)
        await self.author_settings.update_voice_channel_bitrate(ctx.channel)
        await ctx.send(embed=disnake.Embed(description=f"Битрейт канала успешно изменён на: `{value}`",
                                           color=disnake.Color.green()), ephemeral=True)

    @voice_channel.sub_command()
    async def limit(self, ctx,
                    value):
        """Изменить лимит пользователей в канале"""
        if not await self.is_channel_author(ctx):
            return await ctx.send("Вы можете использовать команды только в своём канале", ephemeral=True)
        await ctx.channel.edit(user_limit=value)
        await self.author_settings.update_voice_channel_limit(ctx.channel)
        await ctx.send(embed=disnake.Embed(description=f"Лимит канала успешно изменён на: `{value}`",
                                           color=disnake.Color.green()), ephemeral=True)


def setup(bot):
    bot.add_cog(ChannelCommands(bot))
