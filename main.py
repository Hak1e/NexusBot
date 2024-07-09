from core import Nexus
import os
import asyncio
import logging

logger = logging.getLogger(__name__)


async def load_cogs(bot, root_directory):
    bot.load_extensions(root_directory)
    for root, directories, files in os.walk(root_directory):
        for directory in directories:
            if directory == "__pycache__":
                continue
            try:
                bot.load_extensions(f"{root_directory}{directory}/")
            except Exception as e:
                print(f"Load error: {e}")


async def main():
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%d.%m.%Y %H:%M:%S',
                        filename="lobby.log", level=logging.INFO)
    bot = Nexus()
    await bot.connect_to_db()
    await load_cogs(bot, "./cogs/")
    await bot.start(token=os.getenv("TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
