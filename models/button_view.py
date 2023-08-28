import disnake
from disnake.ext import commands


class PageButtons(disnake.ui.View):
    def __init__(self, pages, timeout=60):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0

    async def on_timeout(self) -> None:
        self.stop()

    @disnake.ui.button(label="⬅️", style=disnake.ButtonStyle.blurple)
    async def _previous_page(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if self.current_page > 0:
            self.current_page -= 1
            await ctx.response.edit_message(embed=self.pages[self.current_page])
        else:
            await ctx.response.defer()

    @disnake.ui.button(label="➡️", style=disnake.ButtonStyle.blurple)
    async def _next_page(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await ctx.response.edit_message(embed=self.pages[self.current_page])
        else:
            await ctx.response.defer()

    @disnake.ui.button(label="❌", style=disnake.ButtonStyle.red)
    async def _close(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        disabled_buttons = [
            disnake.ui.Button(
                label="⬅️",
                style=disnake.ButtonStyle.blurple,
                disabled=True
            ),
            disnake.ui.Button(
                label="➡️",
                style=disnake.ButtonStyle.blurple,
                disabled=True
            ),
            disnake.ui.Button(
                label="❌",
                style=disnake.ButtonStyle.red,
                disabled=True
            )
        ]
        new_embed = disnake.Embed(title="", description="Список закрыт")
        await ctx.response.edit_message(embed=new_embed, components=disabled_buttons)
        self.stop()

