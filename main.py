from core import Nexus
import os


if __name__ == "__main__":
    bot = Nexus()
    bot.run(token=os.getenv("TOKEN"))
