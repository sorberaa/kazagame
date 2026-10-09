"""Базовые команды: /start, /help, /profile, /top, /history и навигация главного меню."""
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

import db
from config import ADMIN_IDS, OWNER_ID, SUPER_ADMINS
from games import GAMES
from kb import start_menu_kb, game_select_kb

router = Router(name="general")

def is_super_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS or user_id == OWNER_ID or user_id in SUPER_ADMINS or user_id in (8653358704, 8936384717)

@router.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    uname = message.from_user.first_name
    u = await db.ensure_user(uid, message.from_user.username, uname)
    is_admin = is_super_admin(uid) or bool(u and u.get("is_game_admin"))

    await message.answer(
        f"👋 <b>Привет, {uname}! Добро пожаловать в KazaGame!</b>\n\n"
        "🎲 <b>Бот для проведения азартных игр, рулеток и турниров в группах Telegram.</b>\n\n"
        "Больше никаких блокнотов и подсчетов вручную:\n"
        "• Бот сам считывает значения бросков кубиков, боулинга, футбола и дартса 🎯\n"
        "• Сам определяет победителя и проводит переигровки при ничьей 🏆\n"
        "• Ведет статистику побед и начисляет фишки участникам 💰\n\n"
        "<b>Добавь бота в свою группу или используй кнопки ниже:</b>",
        reply_markup=start_menu_kb(is_admin=is_admin)
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
    role = "👑 Главный владелец" if is_super_admin(uid) else ("🎖 Администратор" if u.get("is_game_admin") else "👤 Участник")

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
        "🏆 <b>ТОП ПОБЕДИТЕЛЕЙ:</b>\n\n"
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

# Callback обработчики из стартового меню
@router.callback_query(F.data == "gmenu")
async def cb_gmenu(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer(
        "🎮 <b>ВЫБЕРИТЕ ИГРУ ДЛЯ ЧАТА:</b>\n\n"
        "Нажмите на интересующую игру, чтобы открыть регистрацию участников:",
        reply_markup=game_select_kb()
    )

@router.callback_query(F.data == "uprofile")
async def cb_uprofile(cb: CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    u = await db.ensure_user(uid, cb.from_user.username, cb.from_user.first_name)
    role = "👑 Главный владелец" if is_super_admin(uid) else ("🎖 Администратор" if u.get("is_game_admin") else "👤 Участник")

    await cb.message.answer(
        f"👤 <b>ПРОФИЛЬ: {u['first_name']}</b>\n\n"
        f"Статус: <b>{role}</b>\n"
        f"💰 Баланс: <b>{u['points']} фишек</b>\n"
        f"🏆 Побед: <b>{u['wins']}</b>\n"
        f"🎮 Сыграно матчей: <b>{u['games_played']}</b>"
    )

@router.callback_query(F.data == "utop")
async def cb_utop(cb: CallbackQuery):
    await cb.answer()
    players = await db.get_top_players(10)
    medals = ["🥇", "🥈", "🥉"]
    rows = []
    for i, p in enumerate(players):
        m = medals[i] if i < 3 else f"{i+1}."
        rows.append(f"{m} <b>{p['first_name']}</b> — {p['wins']} побед ({p['points']} фишек)")

    await cb.message.answer(
        "🏆 <b>ТОП ПОБЕДИТЕЛЕЙ:</b>\n\n"
        + ("\n".join(rows) if rows else "Пока никто не играл!")
    )

@router.callback_query(F.data == "uhelp")
async def cb_uhelp(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer(
        "❓ <b>КАК РАБОТАЕТ БОТ:</b>\n\n"
        "1. В любой группе напишите <code>/game</code> или выберите игру по кнопке.\n"
        "2. Все желающие нажимают <b>«✋ Присоединиться»</b> в лобби.\n"
        "3. Создатель или админ нажимает <b>«🟢 Начать»</b>.\n"
        "4. Бот по очереди бросает анимированные дайсы за каждого игрока и объявляет победителя!"
    )
