import disnake
import os
from dotenv import load_dotenv
import asyncio
import asyncpg
import logging
import typing as t


class Database:
    def __init__(self):
        self.host = os.getenv("HOST")
        self.port: int = os.getenv("PORT") or 5432
        self.user = os.getenv("USER")
        self.password = os.getenv("PASSWORD")
        self.db_name = os.getenv("DATABASE_NAME")
        # self.conn = await asyncpg.connect(
        #     user=self.user,
        #     password=self.password,
        #     database=self.db_name,
        #     host=self.host
        # )
        self.is_closed: bool = False


    async def connect(self):
        conn = await asyncpg.connect("postgresql://pswdasname@localhost/orphea")
        row = await conn.fetchrow(
            "SELECT * FROM guild"
        )
        print(f"Row:\n{row}")
        await conn.close()


