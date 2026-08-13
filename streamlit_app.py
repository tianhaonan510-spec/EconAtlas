# -*- coding: utf-8 -*-
"""Root Streamlit entrypoint for EconAtlas."""

from pathlib import Path
import runpy


APP_PATH = Path(__file__).resolve().parent / "dashboard" / "streamlit_app.py"
runpy.run_path(str(APP_PATH), run_name="__main__")
