import disnake
from disnake.ext import commands


class PageButtons(disnake.ui.View):
    def __init__(self, pages, timeout=60):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0

    async def on_timeout(self) -> None:
        self.stop()

    @disnake.ui.button(label="◀◀", style=disnake.ButtonStyle.blurple)
    async def first_page(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if self.current_page != 0:
            self.current_page = 0
            await ctx.response.edit_message(embed=self.pages[self.current_page])
        else:
            await ctx.response.defer()

    @disnake.ui.button(label="◀", style=disnake.ButtonStyle.blurple)
    async def previous_page(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if self.current_page > 0:
            self.current_page -= 1
            await ctx.response.edit_message(embed=self.pages[self.current_page])
        else:
            await ctx.response.defer()

    @disnake.ui.button(label="▶", style=disnake.ButtonStyle.blurple)
    async def next_page(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await ctx.response.edit_message(embed=self.pages[self.current_page])
        else:
            await ctx.response.defer()

    @disnake.ui.button(label="▶▶", style=disnake.ButtonStyle.blurple)
    async def last_page(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if self.current_page != len(self.pages) - 1:
            self.current_page = len(self.pages) - 1
            await ctx.response.edit_message(embed=self.pages[self.current_page])
        else:
            await ctx.response.defer()

    @disnake.ui.button(label="✖️", style=disnake.ButtonStyle.red)
    async def _close(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        await ctx.message.delete()
        self.stop()

