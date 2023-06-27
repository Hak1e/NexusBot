import typing

import disnake
from disnake.ext import commands
from disnake import Permissions
import config

created_channels = []


class OnJoinChannel(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.custom_channel: typing.Optional[disnake.VoiceChannel] = None

    async def create_voice_channel(
            self,
            member: disnake.Member,
    ):
        category = member.guild.get_channel(config.voice_channel_category_id)
        # bot = member.guild.get_member(self.bot.user.id)
        overwrite = disnake.PermissionOverwrite(
            view_channel=True,
            manage_permissions=True,
            manage_channels=True
        )

        channel = await member.guild.create_voice_channel(
            name=f"{member.name}'s channel",
            category=category,
            overwrites=category.overwrites
        )
        created_channels.append(channel)
        await channel.set_permissions(member, overwrite=overwrite)

        await member.move_to(channel)

        return channel

    async def voice_state_log(
            self,
            member: disnake.Member,
            before: disnake.VoiceState,
            current: disnake.VoiceState,
    ):
        if before.channel is None and current.channel is not None:
            print(f"{member.name} зашёл в {current.channel.name}")

        elif before.channel is not None and current.channel is not None:
            previous_channel_name = before.channel.name
            print(f"{member.name} перешёл из {previous_channel_name} в {current.channel.name}")

        elif before.channel is not None and current.channel is None:
            print(f"{member.name} покинул канал {before.channel.name}")

    @commands.Cog.listener()
    async def on_voice_state_update(
            self,
            member: disnake.Member,
            before: disnake.VoiceState,
            current: disnake.VoiceState,
    ):

        if member.guild.id != 427777465176424449:
            return

        if before.channel == current.channel:
            return

        # await self.voice_state_log(
        #     member=member,
        #     before=before,
        #     current=current
        # )

        if current.channel is not None and current.channel.id == config.create_voice_channel_id:
            self.custom_channel = await self.create_voice_channel(member=member)

        if before.channel is not None and before.channel in created_channels:
            if not before.channel.members:
                await before.channel.delete()


def setup(bot):
    bot.add_cog(OnJoinChannel(bot))
