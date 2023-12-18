import disnake
from disnake.ext import commands


class PageButtons(disnake.ui.View):
    def __init__(self, pages, timeout=60):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0

    async def on_timeout(self) -> None:
        self.stop()

    async def updated_buttons(self, ctx,
                              btn_left=False, btn_right=False):
        component: list = ctx.message.components.copy()
        custom_buttons_ids = [button.custom_id for button in component[0].children]

        updated_buttons = [
            disnake.ui.Button(
                label="◀◀",
                style=disnake.ButtonStyle.blurple,
                disabled=btn_left,
                custom_id=custom_buttons_ids[0]
            ),
            disnake.ui.Button(
                label="◀",
                style=disnake.ButtonStyle.blurple,
                disabled=btn_left,
                custom_id=custom_buttons_ids[1]
            ),
            disnake.ui.Button(
                label="▶",
                style=disnake.ButtonStyle.blurple,
                disabled=btn_right,
                custom_id=custom_buttons_ids[2]
            ),
            disnake.ui.Button(
                label="▶▶",
                style=disnake.ButtonStyle.blurple,
                disabled=btn_right,
                custom_id=custom_buttons_ids[3]
            ),
            disnake.ui.Button(
                label="✖️",
                style=disnake.ButtonStyle.red,
                disabled=False,
                custom_id=custom_buttons_ids[4]
            )
        ]
        return updated_buttons

    @disnake.ui.button(label="◀◀", style=disnake.ButtonStyle.blurple)
    async def first_page(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if self.current_page != 0:
            self.current_page = 0
            buttons = await self.updated_buttons(ctx, btn_left=True)
            await ctx.response.edit_message(embed=self.pages[self.current_page],
                                            components=buttons)
        else:
            await ctx.response.defer()

    @disnake.ui.button(label="◀", style=disnake.ButtonStyle.blurple)
    async def previous_page(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if self.current_page > 0:
            self.current_page -= 1
            if self.current_page == 0:
                buttons = await self.updated_buttons(ctx, btn_left=True)
                await ctx.response.edit_message(embed=self.pages[self.current_page],
                                                components=buttons)
            else:
                await ctx.response.edit_message(embed=self.pages[self.current_page])
        else:
            await ctx.response.defer()

    @disnake.ui.button(label="▶", style=disnake.ButtonStyle.blurple)
    async def next_page(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            if self.current_page == len(self.pages) - 1:
                buttons = await self.updated_buttons(ctx, btn_right=True)
                await ctx.response.edit_message(embed=self.pages[self.current_page],
                                                components=buttons)
            else:
                await ctx.response.edit_message(embed=self.pages[self.current_page])
        else:
            await ctx.response.defer()

    @disnake.ui.button(label="▶▶", style=disnake.ButtonStyle.blurple)
    async def last_page(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        if self.current_page != len(self.pages) - 1:
            self.current_page = len(self.pages) - 1
            buttons = await self.updated_buttons(ctx, btn_right=True)
            await ctx.response.edit_message(embed=self.pages[self.current_page],
                                            components=buttons)
        else:
            await ctx.response.defer()

    @disnake.ui.button(label="✖️", style=disnake.ButtonStyle.red)
    async def _close(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        await ctx.message.delete()
        self.stop()
