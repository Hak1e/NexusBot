import hikari
import lightbulb
from dotenv import load_dotenv
import os

load_dotenv()
intents = hikari.Intents.ALL
bot = lightbulb.BotApp(
    token=os.getenv("TOKEN"),
    intents=intents,
    banner=None
)
bot.load_extensions_from("./extensions/")

if __name__ == "__main__":
    bot.run()
