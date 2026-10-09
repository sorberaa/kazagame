"""Админ-панель: назначение игровых админов, поиск и карточки игроков, сброс игр, рассылка и статистика."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton as Btn

import db
from config import ADMIN_IDS, OWNER_ID, SUPER_ADMINS
from games import GAMES
from kb import admin_panel_kb, admin_game_pick_kb, back_kb, cancel_fsm_kb, user_manage_kb

router = Router(name="admin")

class AdminFSM(StatesGroup):
    waiting_admin_input = State()
    waiting_search_input = State()
    waiting_broadcast_text = State()

def is_super_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS or user_id == OWNER_ID or user_id in SUPER_ADMINS or user_id in (8653358704, 8936384717)

async def check_admin_access(user_id: int) -> bool:
    if is_super_admin(user_id):
        return True
    u = await db.get_user(user_id)
    return bool(u and u.get("is_game_admin"))

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    uid = message.from_user.id
    if not await check_admin_access(uid):
        return await message.answer("❌ У вас нет доступа к админ-панели.")
    await state.clear()
    await message.answer(
        "👑 <b>ГЛАВНАЯ АДМИН-ПАНЕЛЬ KAZAGAME</b>\n\n"
        "Удобное управление ботом, правами администраторов, участниками и играми.\n\n"
        "Выберите раздел:",
        reply_markup=admin_panel_kb()
    )

@router.message(Command("addadmin"))
async def cmd_addadmin(message: Message):
    uid = message.from_user.id
    if not is_super_admin(uid):
        return await message.answer("❌ Назначать админов могут только главные владельцы.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer(
            "Использование команды:\n"
            "<code>/addadmin ID_ПОЛЬЗОВАТЕЛЯ</code> или <code>/addadmin @юзернейм</code>\n\n"
            "Пример: <code>/addadmin 8653358704</code>"
        )
    target_str = parts[1].strip()
    target = None
    if target_str.isdigit():
        new_id = int(target_str)
        target = await db.get_user(new_id)
        if not target:
            target = await db.ensure_user(new_id, None, f"Admin_{new_id}")
    else:
        target = await db.get_user_by_username(target_str)
        if not target:
            return await message.answer(f"❌ Пользователь с юзернеймом {target_str} ещё не запускал бота и не найден в базе. Попросите его нажать /start или укажите его цифровой Telegram ID.")

    await db.update_user(target["user_id"], is_game_admin=1)
    await message.answer(
        f"✅ <b>Пользователь успешно назначен администратором!</b>\n\n"
        f"👤 Имя: <b>{target['first_name']}</b>\n"
        f"🆔 ID: <code>{target['user_id']}</code>\n"
        f"👑 Теперь у него есть доступ к командам администрирования и проведению игр.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[Btn(text="👤 Открыть карточку", callback_data=f"adm:u:{target['user_id']}")], [Btn(text="👑 В админку", callback_data="adm:main")]])
    )

@router.callback_query(F.data.startswith("adm:"))
async def cb_admin(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    if not await check_admin_access(uid):
        return await cb.answer("У вас нет прав администратора!", show_alert=True)

    parts = cb.data.split(":")
    action = parts[1]
    await cb.answer()

    if action == "main":
        await state.clear()
        await cb.message.edit_text(
            "👑 <b>ГЛАВНАЯ АДМИН-ПАНЕЛЬ KAZAGAME</b>\n\n"
            "Удобное управление ботом, правами администраторов, участниками и играми.\n\n"
            "Выберите раздел:",
            reply_markup=admin_panel_kb()
        )

    elif action == "close":
        await state.clear()
        await cb.message.delete()

    elif action == "cancel_fsm":
        await state.clear()
        await cb.message.edit_text(
            "Операция отменена. Возврат в админ-панель:",
            reply_markup=admin_panel_kb()
        )

    elif action == "stats":
        s = await db.get_stats()
        await cb.message.edit_text(
            "📊 <b>СТАТИСТИКА БОТА KAZAGAME</b>\n\n"
            f"👥 Всего пользователей: <b>{s['users']}</b>\n"
            f"🎲 Сыграно турниров и матчей: <b>{s['games_total']}</b>\n"
            f"💰 Всего фишек у игроков: <b>{s['total_points']}</b>\n"
            f"🚫 Заблокировано пользователей: <b>{s['banned']}</b>\n\n"
            "<i>Все сессии фиксируются автоматически без ошибок.</i>",
            reply_markup=back_kb("adm:main")
        )

    elif action == "admins":
        game_adms = await db.get_game_admins()
        owner_str = "\n".join([f"👑 <code>{i}</code> (Главный владелец)" for i in SUPER_ADMINS])
        mod_lines = []
        rows = []
        for a in game_adms:
            if a["user_id"] not in SUPER_ADMINS:
                mod_lines.append(f"🎖 <b>{a['first_name']}</b> (@{a['username'] or '—'}) — <code>{a['user_id']}</code>")
                rows.append([Btn(text=f"⚙️ {a['first_name']} ({a['user_id']})", callback_data=f"adm:u:{a['user_id']}")])

        msg_text = (
            "👑 <b>СПИСОК АДМИНИСТРАТОРОВ</b>\n\n"
            f"<b>Главные администраторы:</b>\n{owner_str}\n\n"
            f"<b>Игровые модераторы ({len(mod_lines)}):</b>\n"
            + ("\n".join(mod_lines) if mod_lines else "<i>Пока нет дополнительных админов.</i>")
            + "\n\n<i>Нажмите «➕ Добавить админа», чтобы дать права новому человеку.</i>"
        )
        rows.append([Btn(text="➕ Добавить админа", callback_data="adm:add_admin")])
        rows.append([Btn(text="◀️ Назад в админку", callback_data="adm:main")])
        await cb.message.edit_text(msg_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))

    elif action == "add_admin":
        if not is_super_admin(uid):
            return await cb.answer("Назначать новых админов может только главный владелец!", show_alert=True)
        await state.set_state(AdminFSM.waiting_admin_input)
        await cb.message.edit_text(
            "➕ <b>ДОБАВЛЕНИЕ НОВОГО АДМИНИСТРАТОРА</b>\n\n"
            "Отправьте сообщением в чат:\n"
            "• Цифровой <b>Telegram ID</b> (например: <code>8653358704</code>)\n"
            "• Либо <b>@username</b> пользователя (если он уже писал боту)\n\n"
            "<i>Или воспользуйтесь быстрой командой:</i> <code>/addadmin ID</code>",
            reply_markup=cancel_fsm_kb("adm:admins")
        )

    elif action == "search_user":
        await state.set_state(AdminFSM.waiting_search_input)
        await cb.message.edit_text(
            "🔍 <b>ПОИСК ИГРОКА</b>\n\n"
            "Отправьте сообщением в чат:\n"
            "• Telegram ID (цифры)\n"
            "• Либо @username\n"
            "• Либо часть имени пользователя",
            reply_markup=cancel_fsm_kb("adm:main")
        )

    elif action == "users":
        page = int(parts[2]) if len(parts) > 2 else 0
        users = await db.get_all_users()
        per_page = 8
        rows = []
        for pl in users[page*per_page : (page+1)*per_page]:
            mark = "👑 " if (pl["is_game_admin"] or pl["user_id"] in SUPER_ADMINS) else ""
            mark += "🚫 " if pl["is_banned"] else ""
            rows.append([Btn(text=f"{mark}{pl['first_name']} | {pl['points']} 💰", callback_data=f"adm:u:{pl['user_id']}")])

        nav = []
        if page > 0:
            nav.append(Btn(text="◀️", callback_data=f"adm:users:{page-1}"))
        if (page+1)*per_page < len(users):
            nav.append(Btn(text="▶️", callback_data=f"adm:users:{page+1}"))
        if nav:
            rows.append(nav)
        rows.append([Btn(text="🔍 Найти игрока", callback_data="adm:search_user")])
        rows.append([Btn(text="◀️ Назад в админку", callback_data="adm:main")])

        await cb.message.edit_text(
            f"👥 <b>СПИСОК ИГРОКОВ (Всего: {len(users)})</b>\n\n"
            "Выберите игрока для управления балансом, блокировкой или правами админа:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )

    elif action == "u":
        target_id = int(parts[2])
        target = await db.get_user(target_id)
        if not target:
            return await cb.message.edit_text("❌ Игрок не найден в базе данных.", reply_markup=back_kb("adm:users:0"))

        role = "Главный владелец" if target_id in SUPER_ADMINS else ("Игровой админ" if target["is_game_admin"] else "Участник")
        status = "🚫 Заблокирован" if target["is_banned"] else "✅ Активен"
        await cb.message.edit_text(
            f"👤 <b>КАРТОЧКА ПОЛЬЗОВАТЕЛЯ</b>\n\n"
            f"Имя: <b>{target['first_name']}</b> (@{target['username'] or 'нет юзернейма'})\n"
            f"ID: <code>{target['user_id']}</code>\n"
            f"Роль: <b>{role}</b>\n"
            f"Статус: {status}\n\n"
            f"💰 Баланс: <b>{target['points']} фишек</b>\n"
            f"🏆 Побед: <b>{target['wins']}</b> (сыграно {target['games_played']} игр)",
            reply_markup=user_manage_kb(target_id, target)
        )

    elif action == "toggle_adm":
        target_id = int(parts[2])
        if target_id in SUPER_ADMINS:
            return await cb.answer("Нельзя изменить статус главного владельца!", show_alert=True)
        if not is_super_admin(uid):
            return await cb.answer("Изменять статус админа может только главный владелец!", show_alert=True)

        target = await db.get_user(target_id)
        new_val = 0 if target["is_game_admin"] else 1
        await db.update_user(target_id, is_game_admin=new_val)
        target = await db.get_user(target_id)
        role = "Игровой админ" if target["is_game_admin"] else "Участник"
        await cb.answer(f"Статус изменен: {role}")

        status = "🚫 Заблокирован" if target["is_banned"] else "✅ Активен"
        await cb.message.edit_text(
            f"👤 <b>КАРТОЧКА ПОЛЬЗОВАТЕЛЯ (Обновлено)</b>\n\n"
            f"Имя: <b>{target['first_name']}</b> (@{target['username'] or '—'})\n"
            f"ID: <code>{target['user_id']}</code>\n"
            f"Роль: <b>{role}</b>\n"
            f"Статус: {status}\n\n"
            f"💰 Баланс: <b>{target['points']} фишек</b>\n"
            f"🏆 Побед: <b>{target['wins']}</b>",
            reply_markup=user_manage_kb(target_id, target)
        )

    elif action == "toggle_ban":
        target_id = int(parts[2])
        if target_id in SUPER_ADMINS:
            return await cb.answer("Нельзя заблокировать главного владельца!", show_alert=True)

        target = await db.get_user(target_id)
        new_ban = 0 if target["is_banned"] else 1
        await db.update_user(target_id, is_banned=new_ban)
        target = await db.get_user(target_id)
        await cb.answer("Статус блокировки изменен!")

        role = "Главный владелец" if target_id in SUPER_ADMINS else ("Игровой админ" if target["is_game_admin"] else "Участник")
        status = "🚫 Заблокирован" if target["is_banned"] else "✅ Активен"
        await cb.message.edit_text(
            f"👤 <b>КАРТОЧКА ПОЛЬЗОВАТЕЛЯ (Обновлено)</b>\n\n"
            f"Имя: <b>{target['first_name']}</b> (@{target['username'] or '—'})\n"
            f"ID: <code>{target['user_id']}</code>\n"
            f"Роль: <b>{role}</b>\n"
            f"Статус: {status}\n\n"
            f"💰 Баланс: <b>{target['points']} фишек</b>",
            reply_markup=user_manage_kb(target_id, target)
        )

    elif action == "pts_add":
        target_id = int(parts[2])
        amt = int(parts[3]) if len(parts) > 3 else 100
        await db.add_points(target_id, amt, reason=f"Начислено админом {uid}")
        await cb.answer(f"+{amt} фишек выдано!")
        target = await db.get_user(target_id)
        role = "Главный владелец" if target_id in SUPER_ADMINS else ("Игровой админ" if target["is_game_admin"] else "Участник")
        status = "🚫 Заблокирован" if target["is_banned"] else "✅ Активен"
        await cb.message.edit_text(
            f"👤 <b>Баланс пополнен на +{amt} фишек!</b>\n\n"
            f"Имя: <b>{target['first_name']}</b>\n"
            f"ID: <code>{target['user_id']}</code>\n"
            f"💰 Новый баланс: <b>{target['points']} фишек</b>",
            reply_markup=user_manage_kb(target_id, target)
        )

    elif action == "pts_sub":
        target_id = int(parts[2])
        amt = int(parts[3]) if len(parts) > 3 else 100
        await db.spend_points(target_id, amt, reason=f"Списано админом {uid}")
        await cb.answer(f"-{amt} фишек списано!")
        target = await db.get_user(target_id)
        await cb.message.edit_text(
            f"👤 <b>С баланса списано {amt} фишек!</b>\n\n"
            f"Имя: <b>{target['first_name']}</b>\n"
            f"ID: <code>{target['user_id']}</code>\n"
            f"💰 Новый баланс: <b>{target['points']} фишек</b>",
            reply_markup=user_manage_kb(target_id, target)
        )

    elif action == "game_pick":
        await cb.message.edit_text(
            "🎲 <b>БЫСТРЫЙ ЗАПУСК ИГРЫ (АДМИНИСТРАТОР)</b>\n\n"
            "Выберите игру для немедленного открытия лобби в текущем чате:",
            reply_markup=admin_game_pick_kb()
        )

    elif action == "reset_chat":
        chat_id = cb.message.chat.id
        active = await db.get_active_session_in_chat(chat_id)
        if active:
            await db.cancel_session(active["id"])
            await cb.answer("Игра сброшена!")
            await cb.message.answer(f"🛑 <b>Администратор принудительно сбросил игру #{active['id']} ({GAMES.get(active['game_type'], {}).get('name', 'Игра')}).</b>")
        else:
            await cb.answer("В этом чате нет активных зависших игр.", show_alert=True)

    elif action == "broadcast":
        if not is_super_admin(uid):
            return await cb.answer("Рассылка доступна только главному владельцу!", show_alert=True)
        await state.set_state(AdminFSM.waiting_broadcast_text)
        await cb.message.edit_text(
            "📢 <b>РАССЫЛКА ВСЕМ ПОЛЬЗОВАТЕЛЯМ</b>\n\n"
            "Отправьте текст сообщения, который получат все зарегистрированные пользователи бота.\n"
            "Поддерживается HTML разметка (жирный, курсив, ссылки).",
            reply_markup=cancel_fsm_kb("adm:main")
        )

# FSM Обработчики
@router.message(AdminFSM.waiting_admin_input)
async def fsm_add_admin_msg(message: Message, state: FSMContext):
    uid = message.from_user.id
    if not is_super_admin(uid):
        await state.clear()
        return

    text = message.text.strip()
    target = None
    if text.isdigit():
        new_id = int(text)
        target = await db.get_user(new_id)
        if not target:
            target = await db.ensure_user(new_id, None, f"Admin_{new_id}")
    else:
        target = await db.get_user_by_username(text)
        if not target:
            return await message.answer(
                f"❌ Пользователь <b>{text}</b> не найден в базе данных.\n\n"
                "Пользователь должен хотя бы раз нажать /start в боте, либо укажите его цифровой Telegram ID (узнать ID можно через @userinfobot).",
                reply_markup=cancel_fsm_kb("adm:admins")
            )

    await db.update_user(target["user_id"], is_game_admin=1)
    await state.clear()
    await message.answer(
        f"✅ <b>Администратор успешно назначен!</b>\n\n"
        f"👤 Имя: <b>{target['first_name']}</b>\n"
        f"🆔 ID: <code>{target['user_id']}</code>\n"
        f"👑 Пользователь теперь имеет права игрового админа.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [Btn(text="👤 Карточка админа", callback_data=f"adm:u:{target['user_id']}")],
            [Btn(text="👑 Вернуться в админку", callback_data="adm:main")]
        ])
    )

@router.message(AdminFSM.waiting_search_input)
async def fsm_search_user_msg(message: Message, state: FSMContext):
    uid = message.from_user.id
    if not await check_admin_access(uid):
        await state.clear()
        return

    q = message.text.strip()
    results = await db.search_users(q)
    await state.clear()

    if not results:
        return await message.answer(
            f"❌ По запросу <code>{q}</code> ничего не найдено.",
            reply_markup=back_kb("adm:users:0")
        )

    rows = []
    for r in results[:10]:
        mark = "👑 " if (r["is_game_admin"] or r["user_id"] in SUPER_ADMINS) else ""
        rows.append([Btn(text=f"{mark}{r['first_name']} (@{r['username'] or '—'}) [{r['points']} 💰]", callback_data=f"adm:u:{r['user_id']}")])
    rows.append([Btn(text="◀️ Назад в админку", callback_data="adm:main")])

    await message.answer(
        f"🔍 Результаты поиска по запросу «<b>{q}</b>» ({len(results)} найдено):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )

@router.message(AdminFSM.waiting_broadcast_text)
async def fsm_broadcast_msg(message: Message, state: FSMContext):
    uid = message.from_user.id
    if not is_super_admin(uid):
        await state.clear()
        return

    b_text = message.text
    await state.clear()
    users = await db.get_all_users()

    sent = 0
    fail = 0
    await message.answer(f"⏳ Запускаем рассылку на {len(users)} пользователей...")

    for u in users:
        try:
            await message.bot.send_message(u["user_id"], b_text)
            sent += 1
        except Exception:
            fail += 1

    await message.answer(
        f"📢 <b>Рассылка завершена!</b>\n\n"
        f"✅ Доставлено: <b>{sent}</b>\n"
        f"❌ Не удалось доставить (бот заблокирован пользователем): <b>{fail}</b>",
        reply_markup=back_kb("adm:main")
    )
