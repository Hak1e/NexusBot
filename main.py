from core import Nexus
import os


bot = Nexus()


if __name__ == "__main__":
    # bot.load_extensions("./cogs/")
    bot.run(token=os.getenv("TOKEN"))
