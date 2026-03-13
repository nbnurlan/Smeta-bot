import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from db import init_db
from handlers import common, master, client, stats, chat

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Render uchun soxta veb-server ---
async def handle_ping(request):
    return web.Response(text="Bot ishlayapti! (Render porti ochiq)")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render o'zi beradigan portni topamiz, topolmasa 10000 ni ishlatamiz
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🌐 Soxta veb-server {port}-portda ishga tushdi")
# ------------------------------------

async def main():
    await init_db()
    logger.info("✅ Ma'lumotlar bazasi tayyor.")

    # Botdan oldin veb-serverni ishga tushiramiz
    await start_web_server()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(common.router)
    dp.include_router(master.router)
    dp.include_router(client.router)
    dp.include_router(stats.router)
    dp.include_router(chat.router)

    logger.info("🤖 Bot ishga tushmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
    
