from __future__ import annotations

from typing import TYPE_CHECKING

from parapy.webgui import html, mui
from parapy.webgui.app_bar import AppBar
from parapy.webgui.core import Component, get_asset_url
from parapy.webgui.layout import Box
from parapy.webgui.mui.themes import DefaultTheme

if TYPE_CHECKING:
    from parapy.webgui.core.node import NodeType


class App(Component):
    def render(self) -> NodeType:
        return mui.ThemeProvider(theme=DefaultTheme)[
            AppBar(title="ParaPy app"),
            Box(orientation="vertical", h_align="center")[
                html.img(src=get_asset_url("logo.png")),
                (
                    "This application has been bootstrapped with "
                    "parapy-create-app on 2024-11-24 at 11:21."
                ),
                html.a(href="https://parapy.nl/docs/webgui/latest/")[
                    "Learn ParaPy WebGUI"
                ],
            ],
        ]


if __name__ == "__main__":
    from parapy.webgui.core import display

    display(App, reload=True)
