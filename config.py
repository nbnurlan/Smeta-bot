from dotenv import load_dotenv
import os

load_dotenv()

# Qavs ichida faqat o'zgaruvchilarning NOMI bo'lishi kerak, haqiqiy parollar emas!
BOT_TOKEN: str = os.getenv("BOT_TOKEN")
MASTER_PASSWORD: str = os.getenv("MASTER_PASSWORD")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! Render yoki .env faylini tekshiring.")
    
