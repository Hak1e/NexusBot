import disnake
from disnake.ext import commands
import os
from dotenv import load_dotenv



load_dotenv()
intents = disnake.Intents.guilds | disnake.Intents.emojis

    # | disnake.Intents.reactions
    #| disnake.Intents.messages


bot = commands.InteractionBot(intents=intents)
bot.load_extensions("./cogs/")


@bot.slash_command()
async def ping(ctx: disnake.CommandInteraction):
    """Проверить, находится ли бот в сети"""
    await ctx.send("Pong!")


@bot.event
async def on_ready():
    print(f"{bot.user} has started!")


if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))
