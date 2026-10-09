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

    # 1. Если команда отправлена ответом (Reply) на чье-то сообщение в группе/чате
    if message.reply_to_message and message.reply_to_message.from_user:
        target_u = message.reply_to_message.from_user
        if target_u.is_bot:
            return await message.answer("❌ Бота нельзя назначить администратором.")
        target_id = target_u.id
        target = await db.get_user(target_id)
        if not target:
            target = await db.ensure_user(target_id, target_u.username, target_u.first_name)
        await db.update_user(target_id, is_game_admin=1)
        return await message.answer(
            f"✅ <b>{target_u.first_name} успешно назначен администратором!</b>\n\n"
            f"🆔 ID: <code>{target_id}</code> (@{target_u.username or '—'})\n"
            f"👑 Пользователь получил полный доступ к проведению игр.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [Btn(text="👤 Карточка пользователя", callback_data=f"adm:u:{target_id}")],
                [Btn(text="👑 В админку", callback_data="adm:main")]
            ])
        )

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer(
            "👑 <b>КАК НАЗНАЧИТЬ АДМИНИСТРАТОРА:</b>\n\n"
            "• <b>Способ 1 (самый легкий):</b> ответьте на любое сообщение человека командой <code>/addadmin</code>\n"
            "• <b>Способ 2 (по ID):</b> <code>/addadmin 123456789</code>\n"
            "• <b>Способ 3 (по @username):</b> <code>/addadmin @username</code> (если он уже писал боту)\n"
            "• <b>Способ 4:</b> /admin ➔ «👑 Админы» ➔ «👥 Выбрать из списка игроков»",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[Btn(text="👑 Открыть админку", callback_data="adm:main")]])
        )

    target_str = parts[1].strip()
    target = None
    if target_str.isdigit():
        new_id = int(target_str)
        target = await db.get_user(new_id)
        if not target:
            target = await db.ensure_user(new_id, None, f"Admin_{new_id}")
    else:
        uname = target_str.lstrip("@").strip()
        target = await db.get_user_by_username(uname)
        if not target:
            return await message.answer(
                f"⚠️ <b>Пользователь @{uname} ещё не найден в базе бота!</b>\n\n"
                "Telegram не передает ботам информацию о незнакомых пользователях только по @юзернейму, пока они хотя бы раз не нажали /start или не сыграли в чате.\n\n"
                "<b>Решение:</b>\n"
                "1. Ответьте на его сообщение командой <code>/addadmin</code>\n"
                "2. Или укажите его цифровой Telegram ID: <code>/addadmin ЦИФРЫ</code>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[Btn(text="👑 В админку", callback_data="adm:main")]])
            )

    await db.update_user(target["user_id"], is_game_admin=1)
    await message.answer(
        f"✅ <b>Пользователь успешно назначен администратором!</b>\n\n"
        f"👤 Имя: <b>{target['first_name']}</b>\n"
        f"🆔 ID: <code>{target['user_id']}</code> (@{target.get('username') or '—'})\n"
        f"👑 Теперь у него есть доступ к командам администрирования и проведению игр.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [Btn(text="👤 Открыть карточку", callback_data=f"adm:u:{target['user_id']}")],
            [Btn(text="👑 В админку", callback_data="adm:main")]
        ])
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
            + "\n\n<i>Выберите, как добавить нового админа:</i>"
        )
        rows.append([Btn(text="👥 Выбрать из списка игроков (1 клик)", callback_data="adm:pick_admin_user:0")])
        rows.append([Btn(text="➕ Ввести ID или переслать сообщение", callback_data="adm:add_admin")])
        rows.append([Btn(text="◀️ Назад в админку", callback_data="adm:main")])
        await cb.message.edit_text(msg_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))

    elif action == "pick_admin_user":
        page = int(parts[2]) if len(parts) > 2 else 0
        users = await db.get_all_users()
        non_admins = [u for u in users if not u.get("is_game_admin") and u["user_id"] not in SUPER_ADMINS]

        if not non_admins:
            return await cb.message.edit_text(
                "👥 <b>ВЫБОР ИЗ СПИСКА ИГРОКОВ</b>\n\n"
                "Все текущие игроки в базе уже назначены админами, либо других игроков пока нет.\n\n"
                "Вы можете назначить нового админа по его Telegram ID:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [Btn(text="➕ Ввести ID вручную", callback_data="adm:add_admin")],
                    [Btn(text="◀️ Назад к админам", callback_data="adm:admins")]
                ])
            )

        per_page = 6
        rows = []
        for pl in non_admins[page*per_page : (page+1)*per_page]:
            rows.append([
                Btn(text=f"👤 {pl['first_name']} (@{pl.get('username') or pl['user_id']})", callback_data=f"adm:u:{pl['user_id']}"),
                Btn(text="👑 Сделать админом", callback_data=f"adm:make_adm_direct:{pl['user_id']}")
            ])

        nav = []
        if page > 0:
            nav.append(Btn(text="◀️", callback_data=f"adm:pick_admin_user:{page-1}"))
        if (page+1)*per_page < len(non_admins):
            nav.append(Btn(text="▶️", callback_data=f"adm:pick_admin_user:{page+1}"))
        if nav:
            rows.append(nav)
        rows.append([Btn(text="◀️ Назад к админам", callback_data="adm:admins")])

        await cb.message.edit_text(
            f"👥 <b>ВЫБОР ИЗ ИГРОКОВ (Доступно: {len(non_admins)})</b>\n\n"
            "Нажмите <b>«👑 Сделать админом»</b> напротив нужного человека:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )

    elif action == "make_adm_direct":
        if not is_super_admin(uid):
            return await cb.answer("Только главный владелец может назначать админов!", show_alert=True)
        target_id = int(parts[2])
        target = await db.get_user(target_id)
        if not target:
            return await cb.answer("Пользователь не найден!", show_alert=True)
        await db.update_user(target_id, is_game_admin=1)
        await cb.answer(f"✅ {target['first_name']} назначен админом!", show_alert=True)

        target = await db.get_user(target_id)
        await cb.message.edit_text(
            f"✅ <b>Пользователь {target['first_name']} успешно назначен администратором!</b>\n\n"
            f"🆔 ID: <code>{target['user_id']}</code> (@{target.get('username') or '—'})\n"
            f"👑 Теперь у него есть доступ к командам администрирования.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [Btn(text="👥 Выбрать ещё админа", callback_data="adm:pick_admin_user:0")],
                [Btn(text="👑 К списку админов", callback_data="adm:admins")]
            ])
        )

    elif action == "add_admin":
        if not is_super_admin(uid):
            return await cb.answer("Назначать новых админов может только главный владелец!", show_alert=True)
        await state.set_state(AdminFSM.waiting_admin_input)
        await cb.message.edit_text(
            "➕ <b>ДОБАВЛЕНИЕ НОВОГО АДМИНИСТРАТОРА</b>\n\n"
            "Отправьте сообщением в этот диалог:\n"
            "• <b>Цифровой Telegram ID</b> (например: <code>8653358704</code>)\n"
            "• <b>Или перешлите любое сообщение</b> от этого человека прямо сюда!\n"
            "• Либо <b>@username</b> пользователя (если он уже запускал бота)\n\n"
            "<i>Также в любой группе можно просто ответить на его сообщение:</i> <code>/addadmin</code>",
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

    target_id = None
    target_name = None
    target_username = None

    # 1. Проверяем пересланное сообщение (forward_origin или forward_from)
    if message.forward_origin:
        sender = getattr(message.forward_origin, "sender_user", None)
        if sender:
            target_id = sender.id
            target_name = sender.first_name
            target_username = sender.username
    elif message.forward_from:
        target_id = message.forward_from.id
        target_name = message.forward_from.first_name
        target_username = message.forward_from.username
    elif message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.first_name
        target_username = message.reply_to_message.from_user.username
    elif message.contact:
        target_id = message.contact.user_id
        target_name = message.contact.first_name

    # 2. Если пересылки нет, парсим текст
    if not target_id and message.text:
        text = message.text.strip()
        if "t.me/" in text:
            text = text.split("t.me/")[-1].split("/")[0].split("?")[0].strip()

        if text.isdigit():
            target_id = int(text)
        else:
            uname = text.lstrip("@").strip()
            target_row = await db.get_user_by_username(uname)
            if target_row:
                target_id = target_row["user_id"]
                target_name = target_row["first_name"]
                target_username = target_row["username"]
            else:
                return await message.answer(
                    f"⚠️ <b>Пользователь @{uname} пока не найден в базе бота!</b>\n\n"
                    "Telegram не позволяет ботам узнать цифровой ID нового пользователя только по @юзернейму, пока он ни разу не контактировал с ботом.\n\n"
                    "<b>Как легко сделать его админом прямо сейчас:</b>\n"
                    "1. <b>В группе:</b> ответьте на любое его сообщение командой <code>/addadmin</code>\n"
                    "2. <b>В этом диалоге:</b> просто перешлите сюда любое его сообщение\n"
                    "3. <b>По ID:</b> отправьте его числовой Telegram ID\n"
                    "4. Попросите его нажать /start в боте, после чего повторите ввод @юзернейма.",
                    reply_markup=cancel_fsm_kb("adm:admins")
                )

    if not target_id:
        return await message.answer(
            "❌ Не удалось определить пользователя.\nОтправьте цифровой Telegram ID или просто перешлите любое сообщение от пользователя сюда в чат.",
            reply_markup=cancel_fsm_kb("adm:admins")
        )

    target = await db.get_user(target_id)
    if not target:
        target = await db.ensure_user(target_id, target_username, target_name or f"User_{target_id}")
    elif target_name or target_username:
        await db.ensure_user(target_id, target_username or target.get("username"), target_name or target.get("first_name"))

    await db.update_user(target_id, is_game_admin=1)
    await state.clear()
    await message.answer(
        f"✅ <b>Администратор успешно назначен!</b>\n\n"
        f"👤 Имя: <b>{target['first_name']}</b>\n"
        f"🆔 ID: <code>{target['user_id']}</code> (@{target.get('username') or 'нет юзернейма'})\n"
        f"👑 Теперь у него есть права игрового администратора.",
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

    q = message.text.strip() if message.text else ""
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
