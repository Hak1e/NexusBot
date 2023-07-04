import disnake
from disnake.ext import commands
from asyncpg import Pool
import os
from dotenv import load_dotenv
from core.db import Database
import typing as t

class Nexus(commands.InteractionBot):
    def __init__(self) -> None:
        intents = disnake.Intents.all()
        super().__init__(intents=intents)
        self._db = Database()
        self._pool = None
        self.bot = commands.InteractionBot
        self.persistent_views_added = False

    async def connect_to_db(self):
        print("Подключаюсь к базе данных")
        await self._db.connect()
        self._pool = self._db.get_pool()
        print(f"Подключено")

    async def on_ready(self):
        await self.connect_to_db()
        self.bot.load_extensions(self, "./cogs/")
        print(f"Бот {self.user} готов к работе!")

    def get_db(self):
        return self._db

    def get_pool(self):
        return self._pool








