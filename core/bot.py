import disnake
from disnake.ext import commands
from core.db import Database
import datetime
import traceback
import sys


class Nexus(commands.InteractionBot):
    def __init__(self) -> None:
        intents = disnake.Intents.all()
        super().__init__(intents=intents)
        self.db = Database()
        self.pool = None
        self.bot = commands.InteractionBot
        self.persistent_views_added = False

    async def connect_to_db(self):
        print("Подключаюсь к базе данных")
        await self.db.connect()
        self.pool = self.db.get_pool()
        print(f"Подключено")

    async def on_ready(self):
        print(f"Бот {self.user} готов к работе!")
        guilds = await self.bot.fetch_guilds(self).flatten()
        print(f"Активные серверы ({len(guilds)}):")
        counter = 1
        for guild in guilds:
            print(f"{counter}) {guild.name}, id: {guild.id}")
            counter += 1

    async def on_guild_join(self, guild):
        add_guild_to_db_query = ("INSERT INTO guild (id, owner_id) "
                                 "VALUES ($1, $2) "
                                 "ON CONFLICT (id) DO NOTHING")
        await self.pool.execute(add_guild_to_db_query, guild.id,
                                guild.owner_id)

    def get_db(self):
        return self.db

    def get_pool(self):
        return self.pool








