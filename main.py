from core import Nexus
import os
import asyncio


async def load_cogs(bot, root_directory):
    bot.load_extensions("./cogs/")
    for root, directories, files in os.walk(root_directory):
        for directory in directories:
            if directory == "__pycache__":
                print(f"Pycache skipped")
                continue
            try:
                bot.load_extensions(f"{root_directory}{directory}/")
            except Exception as e:
                print(f"Load error: {e}")


async def main():
    bot = Nexus()
    await bot.connect_to_db()
    await load_cogs(bot, "./cogs/")
    await bot.start(token=os.getenv("TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
