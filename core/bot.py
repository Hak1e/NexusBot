import disnake
from disnake.ext import commands
from asyncpg import Pool
import os
from dotenv import load_dotenv
from core.db import Database



class Nexus(commands.InteractionBot):
    def __init__(self) -> None:
        intents = disnake.Intents.all()
        super().__init__(
            intents=intents
        )
        self.db = Database()

    async def on_connect(self):
        print("Подключаюсь")
        # await self.db.connect()  ####
        print("Подключено")

    async def on_ready(self):
        print(f"{self.user} has started!")










