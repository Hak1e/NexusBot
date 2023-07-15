from core import Nexus
import os
import asyncio


async def main():
    bot = Nexus()
    await bot.connect_to_db()
    bot.load_extensions("./cogs/")
    await bot.start(token=os.getenv("TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())

