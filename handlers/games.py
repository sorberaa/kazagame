"""Обработчики игровых сессий: лобби, броски кубиков, автоматический подсчет и рулетка."""
import asyncio
import random
from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

import db
from config import ADMIN_IDS, OWNER_ID
from games import GAMES, format_dice_result
from kb import game_select_kb, lobby_kb

router = Router(name="games")

def is_any_admin(user_id: int, u: dict | None = None) -> bool:
    if user_id in ADMIN_IDS or user_id == OWNER_ID:
        return True
    if u and u.get("is_game_admin"):
        return True
    return False

@router.message(Command("game"))
async def cmd_game(message: Message):
    """Вызов меню выбора игры."""
    if message.chat.type == "private":
        return await message.answer("🎲 Игры предназначены для групп! Добавь бота в свой чат и пиши команду <code>/game</code>")

    # Проверяем нет ли уже активной сессии
    active = await db.get_active_session_in_chat(message.chat.id)
    if active:
        return await message.answer(
            f"⚠️ В этом чате уже запущена игра (Лобби #{active['id']} - {GAMES[active['game_type']]['name']})!\n"
            "Завершите её или отмените перед созданием новой."
        )

    await message.answer(
        "🎮 <b>ВЫБОР ИГРЫ ДЛЯ ЧАТА</b>\n\n"
        "Выберите дисциплину для проведения раунда:\n"
        "• Бот сам соберёт участников\n"
        "• Сам выполнит броски эмодзи/рулетки\n"
        "• Автоматически посчитает очки и объявит чемпиона!",
        reply_markup=game_select_kb()
    )

@router.callback_query(F.data.startswith("gstart:"))
async def cb_game_start(cb: CallbackQuery):
    gkey = cb.data.split(":")[1]
    ginfo = GAMES.get(gkey)
    if not ginfo:
        return await cb.answer("Игра не найдена", show_alert=True)

    chat_id = cb.message.chat.id
    active = await db.get_active_session_in_chat(chat_id)
    if active:
        return await cb.answer("В чате уже есть активная игра!", show_alert=True)

    uid = cb.from_user.id
    uname = cb.from_user.first_name
    await db.ensure_user(uid, cb.from_user.username, uname)

    sid = await db.create_session(
        chat_id=chat_id,
        game_type=gkey,
        creator_id=uid,
        creator_name=uname,
        bet=0,
        target_players=2
    )

    await cb.answer(f"Лобби {ginfo['name']} создано!")
    await cb.message.edit_text(
        f"{ginfo['emoji']} <b>РЕГИСТРАЦИЯ: {ginfo['name'].upper()}</b>\n\n"
        f"Организатор: <b>{uname}</b>\n"
        f"Правила: <i>{ginfo['desc']}</i>\n\n"
        f"👥 <b>Участники (1):</b>\n• <b>{uname}</b> (создатель)\n\n"
        "Жмите кнопку <b>«Присоединиться»</b>, чтобы войти в список игроков! 👇",
        reply_markup=lobby_kb(sid, 1, 2)
    )

@router.callback_query(F.data.startswith("gjoin:"))
async def cb_game_join(cb: CallbackQuery):
    sid = int(cb.data.split(":")[1])
    s = await db.get_session(sid)
    if not s or s["status"] != "lobby":
        return await cb.answer("Лобби уже закрыто или не существует!", show_alert=True)

    uid = cb.from_user.id
    uname = cb.from_user.first_name
    await db.ensure_user(uid, cb.from_user.username, uname)

    ok = await db.join_session(sid, uid, uname)
    if not ok:
        return await cb.answer("Ты уже в игре! ✋", show_alert=True)

    players = await db.get_session_players(sid)
    ginfo = GAMES[s["game_type"]]
    cnt = len(players)
    await cb.answer(f"Ты успешно присоединился! (#{cnt})")

    names_list = "\n".join(f"{i+1}. <b>{p['first_name']}</b>" for i, p in enumerate(players))
    try:
        await cb.message.edit_text(
            f"{ginfo['emoji']} <b>РЕГИСТРАЦИЯ: {ginfo['name'].upper()}</b>\n\n"
            f"Организатор: <b>{s['creator_name']}</b>\n"
            f"Правила: <i>{ginfo['desc']}</i>\n\n"
            f"👥 <b>Участники ({cnt}):</b>\n{names_list}\n\n"
            "Жмите старт, когда все на месте! 👇",
            reply_markup=lobby_kb(sid, cnt, 2)
        )
    except Exception:
        pass

@router.callback_query(F.data.startswith("gcancel:"))
async def cb_game_cancel(cb: CallbackQuery):
    sid = int(cb.data.split(":")[1])
    s = await db.get_session(sid)
    if not s or s["status"] != "lobby":
        return await cb.answer("Лобби уже неактивно", show_alert=True)

    uid = cb.from_user.id
    u = await db.get_user(uid)
    if s["creator_id"] != uid and not is_any_admin(uid, u):
        return await cb.answer("Отменить может только создатель или админ игр!", show_alert=True)

    await db.cancel_session(sid)
    await cb.answer("Игра отменена")
    await cb.message.edit_text(f"❌ <b>Игра «{GAMES[s['game_type']]['name']}» была отменена.</b>")

@router.callback_query(F.data.startswith("gplay:"))
async def cb_game_play(cb: CallbackQuery):
    sid = int(cb.data.split(":")[1])
    s = await db.get_session(sid)
    if not s or s["status"] != "lobby":
        return await cb.answer("Игра уже запущена или отменена", show_alert=True)

    players = await db.get_session_players(sid)
    if len(players) < 2:
        return await cb.answer("Нужно минимум 2 участника!", show_alert=True)

    uid = cb.from_user.id
    u = await db.get_user(uid)
    if s["creator_id"] != uid and not is_any_admin(uid, u):
        return await cb.answer("Запустить может только создатель или админ!", show_alert=True)

    await db.update_user(uid) # ping
    # Ставим статус playing
    async with db._connect() as _db:
        await _db.execute("UPDATE game_sessions SET status = 'playing' WHERE id = ?", (sid,))
        await _db.commit()

    await cb.answer("Начинаем игру!")
    ginfo = GAMES[s["game_type"]]
    bot = cb.bot
    chat_id = cb.message.chat.id

    await cb.message.edit_text(
        f"{ginfo['emoji']} <b>СТАРТ МАТЧА: {ginfo['name'].upper()}!</b>\n\n"
        f"Участников: <b>{len(players)}</b>. Бот начинает автоматические броски! 🎲"
    )

    # 1. Если это РУЛЕТКА
    if s["game_type"] == "roulette":
        anim_msg = await bot.send_message(chat_id, "🎡 <b>Колесо фортуны запущено! Стрелка крутится...</b>")
        for _ in range(3):
            await asyncio.sleep(1.0)
            cur_lucky = random.choice(players)["first_name"]
            await anim_msg.edit_text(f"🎡 <i>Стрелка замедляется около... {cur_lucky}...</i>")

        winner = random.choice(players)
        await asyncio.sleep(1.2)
        await finish_and_announce(bot, chat_id, sid, winner["user_id"], winner["first_name"], s, players, custom_score_text=None)
        return

    # 2. Если это ИГРЫ ТЕЛЕГРАМ ДАЙС (эмодзи)
    dice_emoji = ginfo["dice_emoji"]
    results = []

    for p in players:
        p_name = p["first_name"]
        await bot.send_message(chat_id, f"👉 Очередь игрока: <b>{p_name}</b>...")
        await asyncio.sleep(0.5)

        # Бот бросает официальный эмодзи Telegram
        dice_msg = await bot.send_dice(chat_id, emoji=dice_emoji)
        raw_val = dice_msg.dice.value
        score, desc = format_dice_result(s["game_type"], raw_val)

        # Ждем пока анимация стикера в ТГ проиграется (около 2-3 сек)
        await asyncio.sleep(3.0)
        await bot.send_message(chat_id, f"👤 <b>{p_name}</b>: {desc} (очков: <b>{score}</b>)")
        await db.update_player_score(sid, p["user_id"], score, raw_val)
        results.append({"user_id": p["user_id"], "name": p_name, "score": score, "raw": raw_val})
        await asyncio.sleep(1.0)

    # Сортируем по очкам
    results.sort(key=lambda x: x["score"], reverse=True)
    winner = results[0]

    # Проверка на ничью за 1 место
    ties = [r for r in results if r["score"] == winner["score"]]
    if len(ties) > 1:
        await bot.send_message(chat_id, f"⚔️ <b>НИЧЬЯ МЕЖДУ ЛИДЕРАМИ ({len(ties)} чел.)! Дополнительный решающий бросок!</b>")
        await asyncio.sleep(1.5)
        tie_results = []
        for tp in ties:
            await bot.send_message(chat_id, f"⚡ Решающий бросок: <b>{tp['name']}</b>!")
            d_msg = await bot.send_dice(chat_id, emoji=dice_emoji)
            r_val = d_msg.dice.value
            sc, _ = format_dice_result(s["game_type"], r_val)
            tie_results.append({"user_id": tp["user_id"], "name": tp["name"], "score": sc})
            await asyncio.sleep(3.0)
        tie_results.sort(key=lambda x: x["score"], reverse=True)
        winner = tie_results[0]

    await finish_and_announce(bot, chat_id, sid, winner["user_id"], winner["name"], s, players, results_table=results)


async def finish_and_announce(bot, chat_id: int, sid: int, winner_id: int, winner_name: str, s: dict, players: list, results_table: list | None = None, custom_score_text: str | None = None):
    await db.finish_session(sid, winner_id, winner_name)
    ginfo = GAMES[s["game_type"]]

    # Начисляем призовые очки/фишки
    prize = 50 + len(players) * 10
    await db.add_points(winner_id, prize, reason=f"Победа в {ginfo['name']}")

    table_lines = ""
    if results_table:
        medals = ["🥇", "🥈", "🥉"]
        rows = []
        for i, r in enumerate(results_table):
            m = medals[i] if i < 3 else f"{i+1}."
            rows.append(f"{m} <b>{r['name']}</b> — {r['score']} очк.")
        table_lines = "\n\n📊 <b>Итоговый протокол:</b>\n" + "\n".join(rows)

    await bot.send_message(
        chat_id,
        f"🏆 <b>ИГРА ЗАВЕРШЕНА! ПОБЕДИТЕЛЬ: <b>{winner_name}</b>!</b> 🎉\n\n"
        f"Дисциплина: {ginfo['emoji']} {ginfo['name']}\n"
        f"Приз победителю: <b>+{prize} очков</b>"
        f"{table_lines}\n\n"
        "<i>Администратору не нужно ничего считать — все результаты сохранены в базе!</i> ✅"
    )

# Команды быстрого броска дуэли между 2 игроками
@router.message(Command("dice"))
@router.message(Command("darts"))
@router.message(Command("basket"))
@router.message(Command("foot"))
@router.message(Command("bowl"))
@router.message(Command("slots"))
@router.message(Command("roulette"))
async def cmd_quick_game(message: Message, command: CommandObject):
    """Быстрый запуск игры по шорткату."""
    cmd_map = {
        "dice": "dice",
        "darts": "darts",
        "basket": "basketball",
        "foot": "football",
        "bowl": "bowling",
        "slots": "slots",
        "roulette": "roulette"
    }
    gkey = cmd_map.get(command.command, "dice")
    ginfo = GAMES[gkey]
    active = await db.get_active_session_in_chat(message.chat.id)
    if active:
        return await message.answer(f"⚠️ В чате уже идёт игра ({GAMES[active['game_type']]['name']})!")

    uid = message.from_user.id
    uname = message.from_user.first_name
    await db.ensure_user(uid, message.from_user.username, uname)
    sid = await db.create_session(message.chat.id, gkey, uid, uname)

    await message.answer(
        f"{ginfo['emoji']} <b>РЕГИСТРАЦИЯ: {ginfo['name'].upper()}</b>\n\n"
        f"Организатор: <b>{uname}</b>\n\n"
        f"👥 <b>Участники (1):</b>\n• <b>{uname}</b>\n\n"
        "Нажмите кнопку ниже для участия! 👇",
        reply_markup=lobby_kb(sid, 1, 2)
    )
