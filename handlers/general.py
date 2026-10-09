"""Базовые команды: /start, /help, /profile, /top, /history."""
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

import db
from games import GAMES

router = Router(name="general")

@router.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    uname = message.from_user.first_name
    await db.ensure_user(uid, message.from_user.username, uname)

    await message.answer(
        f"👋 <b>Привет, {uname}! Добро пожаловать в KazaGame!</b>\n\n"
        "🎲 <b>Бот для проведения азартных игр, рулеток и турниров в группах Telegram.</b>\n\n"
        "Больше никаких блокнотов и подсчетов вручную:\n"
        "• Бот сам считывает значения бросков кубиков, боулинга, футбола и дартса 🎯\n"
        "• Сам определяет победителя и проводит переигровки при ничьей 🏆\n"
        "• Ведет статистику побед и начисляет фишки участникам 💰\n\n"
        "<b>Добавь бота в свою группу и используй команды:</b>\n"
        "/game — главное меню выбора игры\n"
        "/dice — запустить кубики 🎲\n"
        "/darts — турнир по дартсу 🎯\n"
        "/basket — баскетбольный матч 🏀\n"
        "/foot — футбольные пенальти ⚽\n"
        "/bowl — боулинг и кегли 🎳\n"
        "/slots — казино и слоты 🎰\n"
        "/roulette — колесо фортуны / рулетка 🎡\n"
        "/top — топ игроков чата 🏆\n"
        "/profile — твой профиль и фишки 👤\n"
        "/admin — админ-панель (для ведущих) 👑"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "❓ <b>КАК РАБОТАЕТ БОТ:</b>\n\n"
        "1. Любой участник или админ пишет <code>/game</code> в группе.\n"
        "2. Выбирается дисциплина (например, Боулинг или Баскетбол).\n"
        "3. Все желающие нажимают кнопку <b>«✋ Присоединиться»</b>.\n"
        "4. Когда игроки набраны — нажимается <b>«🟢 Начать»</b>.\n"
        "5. Бот по очереди бросает анимированные эмодзи Telegram за каждого игрока, "
        "считывает точный результат через API, вычисляет победителя и выдает призы!\n\n"
        "Всё автоматизировано на 100%!"
    )

@router.message(Command("profile"))
async def cmd_profile(message: Message):
    uid = message.from_user.id
    u = await db.ensure_user(uid, message.from_user.username, message.from_user.first_name)
    role = "👑 Администратор" if u.get("is_game_admin") else "👤 Участник"

    await message.answer(
        f"👤 <b>ПРОФИЛЬ: {u['first_name']}</b>\n\n"
        f"Статус: <b>{role}</b>\n"
        f"💰 Баланс: <b>{u['points']} фишек</b>\n"
        f"🏆 Побед: <b>{u['wins']}</b>\n"
        f"🎮 Сыграно матчей: <b>{u['games_played']}</b>"
    )

@router.message(Command("top"))
async def cmd_top(message: Message):
    players = await db.get_top_players(10)
    medals = ["🥇", "🥈", "🥉"]
    rows = []
    for i, p in enumerate(players):
        m = medals[i] if i < 3 else f"{i+1}."
        rows.append(f"{m} <b>{p['first_name']}</b> — {p['wins']} побед ({p['points']} фишек)")

    await message.answer(
        "🏆 <b>ТОП ПОБЕДИТЕЛЕЙ ЧАТА:</b>\n\n"
        + ("\n".join(rows) if rows else "Пока никто не играл!")
    )

@router.message(Command("history"))
async def cmd_history(message: Message):
    hist = await db.get_chat_history(message.chat.id, 8)
    if not hist:
        return await message.answer("В этом чате ещё не завершались игры!")

    rows = []
    for h in hist:
        g = GAMES.get(h["game_type"], {"name": h["game_type"], "emoji": "🎲"})
        rows.append(f"• {g['emoji']} <b>{g['name']}</b>: победитель <b>{h['winner_name']}</b> ({h['players_count']} уч.)")

    await message.answer(
        "📜 <b>ПОСЛЕДНИЕ ИГРЫ В ЧАТЕ:</b>\n\n" + "\n".join(rows)
    )
