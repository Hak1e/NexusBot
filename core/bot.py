import disnake
from disnake.ext import commands
from asyncpg import Pool
import os
from dotenv import load_dotenv
from core.db import Database


class Nexus(commands.InteractionBot):
    def __init__(self) -> None:
        intents = disnake.Intents.all()
        super().__init__(intents=intents)
        self._db = Database()
        self._pool = None
        self.bot = commands.InteractionBot

    async def on_connect(self):
        print("Подключаюсь к базе данных")
        await self._db.connect()
        self._pool = self._db.pool()
        print(f"Подключено")

    async def on_ready(self):
        self.bot.load_extensions(self, "./cogs/")
        print(f"Бот {self.user} готов к работе!")

    @property
    def db(self):
        return self._db

    @property
    def pool(self):
        return self._pool








