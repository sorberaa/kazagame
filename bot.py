"""Точка входа KazaGame — Telegram бот для турниров, дайсов и рулеток в группах."""
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from config import BOT_TOKEN, PORT, SUPER_ADMINS
from db import init_db, ensure_super_admins
from handlers import all_routers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("kazagame")

async def health(_request):
    return web.Response(text="OK - KazaGame is running")

async def start_web():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    log.info("Health check server active on port %s", PORT)
    return runner

async def main():
    if not BOT_TOKEN:
        log.warning("BOT_TOKEN не задан! Бот запущен в режиме ожидания токена.")
        runner = await start_web()
        try:
            while True:
                await asyncio.sleep(3600)
        finally:
            await runner.cleanup()
        return

    await init_db()
    await ensure_super_admins(SUPER_ADMINS)
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    for r in all_routers:
        dp.include_router(r)

    await bot.set_my_commands([
        BotCommand(command="game", description="🎮 Выбор игры для чата"),
        BotCommand(command="dice", description="🎲 Кубики"),
        BotCommand(command="basket", description="🏀 Баскетбол"),
        BotCommand(command="foot", description="⚽ Футбол"),
        BotCommand(command="bowl", description="🎳 Боулинг"),
        BotCommand(command="darts", description="🎯 Дартс"),
        BotCommand(command="slots", description="🎰 Слоты"),
        BotCommand(command="roulette", description="🎡 Рулетка / Розыгрыш"),
        BotCommand(command="top", description="🏆 Топ игроков"),
        BotCommand(command="profile", description="👤 Профиль и баланс"),
        BotCommand(command="history", description="📜 История игр чата"),
        BotCommand(command="admin", description="👑 Админ-панель"),
        BotCommand(command="help", description="❓ Инструкция"),
    ])

    runner = await start_web()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        log.info("Бот KazaGame успешно запущен в режиме polling!")
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())

