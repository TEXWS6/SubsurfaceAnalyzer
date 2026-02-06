"""Application configuration constants."""

import os

APP_TITLE = "SubsurfaceAnalyzer"
APP_HOST = "127.0.0.1"
APP_PORT = 8050
DEBUG = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "subsurface.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)
