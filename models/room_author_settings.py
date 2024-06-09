import asyncpg
import json


class AuthorSettings:
    def __init__(self, bot):
        self.bot = bot
        self.pool: asyncpg.Pool = self.bot.get_pool()

    async def get_voice_channel_author_id(self, voice_channel):
        get_channel_author_id = "SELECT user_id " \
                                "FROM lobby_voice_channel_author " \
                                "WHERE guild_id = $1 and voice_channel_id = $2"
        channel_author_id = await self.pool.fetchval(get_channel_author_id, voice_channel.guild.id,
                                                     voice_channel.id)
        return channel_author_id

    async def update_voice_channel_overwrites(self, voice_channel):
        channel_author_id = await self.get_voice_channel_author_id(voice_channel)
        channel_overwrites = voice_channel.overwrites
        data = []
        for target, permissions in channel_overwrites.items():
            data.append(
                {
                    "target": target.id,
                    "permissions": dict(permissions)
                }
            )
        channel_overwrites_json = json.dumps(data)
        update_channel_settings = ("INSERT INTO lobby_voice_channel_settings ("
                                   "guild_id, user_id, "
                                   "channel_name, bitrate,"
                                   "user_limit, channel_overwrites) "
                                   "VALUES ($1, $2, $3, $4, $5, $6)"
                                   "ON CONFLICT (guild_id, user_id) DO UPDATE "
                                   "SET channel_name = $3, bitrate = $4,"
                                   "user_limit = $5, channel_overwrites = $6")
        await self.pool.execute(update_channel_settings, voice_channel.guild.id,
                                channel_author_id, voice_channel.bitrate,
                                voice_channel.user_limit, channel_overwrites_json)








