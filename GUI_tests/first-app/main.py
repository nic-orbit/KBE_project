import os.path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastapi import FastAPI
from parapy.webgui.core import WebGUI
from src.ui import App

app = FastAPI()
api = WebGUI()
api.init_app(app, App)


if __name__ == "__main__":
    from parapy.webgui.core import display

    display(App, app=app, reload=True)
