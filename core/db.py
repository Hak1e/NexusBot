from contextlib import asynccontextmanager

import disnake
import os
from dotenv import load_dotenv
import asyncpg
import typing

load_dotenv()


class Database:
    def __init__(self):
        self.host = os.getenv("HOST")
        self.port = int(os.getenv("PORT"))
        self.user = os.getenv("USER")
        self.password = os.getenv("PASSWORD")
        self.db_name = os.getenv("DATABASE_NAME")
        self._pool: typing.Optional[asyncpg.Pool] = None
        self.is_closed: bool = False

    async def connect(self):
        self._pool = await asyncpg.create_pool(
            f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"
        )
        self.is_closed = False

    async def close(self):
        if not self.is_closed:
            await self._pool.close()
            self.is_closed = True


    def get_pool(self):
        return self._pool
