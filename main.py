import asyncio
import logging
import os

from core import Nexus

logger = logging.getLogger(__name__)


async def main():
    logging.basicConfig(
        format="%(asctime)s %(message)s",
        datefmt="%d.%m.%Y %H:%M:%S",
        filename="lobby.log",
        level=logging.INFO,
    )
    bot = Nexus()
    await bot.connect_to_db()
    bot.load_extension("cogs", recursive=True)
    await bot.start(token=os.getenv("TOKEN"))


if __name__ == "__main__":
    asyncio.run(main())
