import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("8604814040:AAHq4lSnkwaOEoAeXh7rw-QBQIl51IZqrFI", "")
MASTER_PASSWORD: str = os.getenv("MASTER_PASSWORD", "2026")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN .env faylida belgilanmagan!")
