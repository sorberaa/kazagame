"""Админ-панель: назначение игровых админов, просмотр игроков, сброс сессий и статистика."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton as Btn

import db
from config import ADMIN_IDS, OWNER_ID
from games import GAMES
from kb import admin_panel_kb, back_kb, user_manage_kb

router = Router(name="admin")

def is_super_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS or user_id == OWNER_ID

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    uid = message.from_user.id
    u = await db.get_user(uid)
    if not is_super_admin(uid) and not (u and u.get("is_game_admin")):
        return

    await message.answer(
        "👑 <b>АДМИН-ПАНЕЛЬ KAZAGAME</b>\n\n"
        "Управление игровыми турнирами, правами модераторов и участниками.\n"
        "Выберите действие:",
        reply_markup=admin_panel_kb()
    )

@router.callback_query(F.data.startswith("adm:"))
async def cb_admin(cb: CallbackQuery):
    uid = cb.from_user.id
    u = await db.get_user(uid)
    if not is_super_admin(uid) and not (u and u.get("is_game_admin")):
        return await cb.answer("У вас нет прав администратора!", show_alert=True)

    action = cb.data.split(":")[1]
    await cb.answer()

    if action == "main":
        await cb.message.edit_text(
            "👑 <b>АДМИН-ПАНЕЛЬ KAZAGAME</b>\n\nВыберите действие:",
            reply_markup=admin_panel_kb()
        )
    elif action == "close":
        await cb.message.delete()

    elif action == "stats":
        s = await db.get_stats()
        await cb.message.edit_text(
            "📊 <b>СТАТИСТИКА БОТА</b>\n\n"
            f"👥 Всего игроков в базе: <b>{s['users']}</b>\n"
            f"🎲 Сыграно матчей и турниров: <b>{s['games_total']}</b>\n"
            f"💰 Всего фишек в обороте: <b>{s['total_points']}</b>\n"
            f"🚫 Заблокировано: <b>{s['banned']}</b>\n\n"
            "<i>Все игры регистрируются автоматически!</i>",
            reply_markup=back_kb("adm:main")
        )

    elif action == "admins":
        game_adms = await db.get_game_admins()
        lines = [f"👑 <code>{i}</code> (Главный владелец)" for i in ADMIN_IDS]
        for a in game_adms:
            if a["user_id"] not in ADMIN_IDS:
                lines.append(f"🎖 <b>{a['first_name']}</b> (<code>{a['user_id']}</code>)")
        await cb.message.edit_text(
            "👑 <b>СПИСОК АДМИНИСТРАТОРОВ ИГР</b>\n\n"
            + "\n".join(lines) +
            "\n\n<i>Чтобы назначить или снять админа: открой «Игроки» ➔ выбери человека ➔ «Сделать админом».</i>",
            reply_markup=back_kb("adm:main")
        )

    elif action == "users":
        page = int(cb.data.split(":")[2])
        users = await db.get_all_users()
        per_page = 8
        rows = []
        for pl in users[page*per_page : (page+1)*per_page]:
            mark = "👑 " if (pl["is_game_admin"] or pl["user_id"] in ADMIN_IDS) else ""
            mark += "🚫 " if pl["is_banned"] else ""
            rows.append([Btn(text=f"{mark}{pl['first_name']} ({pl['points']} фишек)", callback_data=f"adm:u:{pl['user_id']}")])

        nav = []
        if page > 0:
            nav.append(Btn(text="◀️", callback_data=f"adm:users:{page-1}"))
        if (page+1)*per_page < len(users):
            nav.append(Btn(text="▶️", callback_data=f"adm:users:{page+1}"))
        if nav:
            rows.append(nav)
        rows.append([Btn(text="◀️ Назад", callback_data="adm:main")])

        await cb.message.edit_text(
            f"👥 <b>Игроки ({len(users)})</b>. Выберите участника для управления:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )

    elif action == "u":
        target_id = int(cb.data.split(":")[2])
        target = await db.get_user(target_id)
        if not target:
            return await cb.message.edit_text("❌ Игрок не найден", reply_markup=back_kb("adm:users:0"))

        role = "Главный владелец" if target_id in ADMIN_IDS else ("Игровой админ" if target["is_game_admin"] else "Участник")
        status = "🚫 Забанен" if target["is_banned"] else "✅ Активен"
        await cb.message.edit_text(
            f"👤 <b>КАРТОЧКА ИГРОКА</b>\n\n"
            f"Имя: <b>{target['first_name']}</b> (@{target['username'] or '—'})\n"
            f"ID: <code>{target['user_id']}</code>\n"
            f"Роль: <b>{role}</b>\n"
            f"Статус: {status}\n\n"
            f"💰 Баланс: <b>{target['points']} фишек</b>\n"
            f"🏆 Побед: <b>{target['wins']}</b> (из {target['games_played']} игр)",
            reply_markup=user_manage_kb(target_id, target)
        )

    elif action == "toggle_adm":
        target_id = int(cb.data.split(":")[2])
        if target_id in ADMIN_IDS:
            return await cb.answer("Нельзя изменить статус главного владельца!", show_alert=True)
        target = await db.get_user(target_id)
        new_val = 0 if target["is_game_admin"] else 1
        await db.update_user(target_id, is_game_admin=new_val)
        await cb.answer("Статус администратора изменен!")
        # Обновляем экран
        target = await db.get_user(target_id)
        role = "Игровой админ" if target["is_game_admin"] else "Участник"
        await cb.message.edit_text(
            f"👤 <b>КАРТОЧКА ИГРОКА (Обновлено)</b>\n\n"
            f"Имя: <b>{target['first_name']}</b>\n"
            f"ID: <code>{target['user_id']}</code>\n"
            f"Роль: <b>{role}</b>\n"
            f"💰 Баланс: <b>{target['points']} фишек</b>",
            reply_markup=user_manage_kb(target_id, target)
        )

    elif action == "toggle_ban":
        target_id = int(cb.data.split(":")[2])
        if target_id in ADMIN_IDS:
            return await cb.answer("Нельзя забанить главного владельца!", show_alert=True)
        target = await db.get_user(target_id)
        new_ban = 0 if target["is_banned"] else 1
        await db.update_user(target_id, is_banned=new_ban)
        await cb.answer("Статус блокировки изменен!")
        target = await db.get_user(target_id)
        await cb.message.edit_text(
            f"👤 <b>КАРТОЧКА ИГРОКА (Обновлено)</b>\n\n"
            f"Имя: <b>{target['first_name']}</b>\n"
            f"Статус: {'🚫 Забанен' if target['is_banned'] else '✅ Активен'}",
            reply_markup=user_manage_kb(target_id, target)
        )

    elif action == "pts_add":
        target_id = int(cb.data.split(":")[2])
        await db.add_points(target_id, 100, reason="Начислено админом")
        await cb.answer("+100 фишек выдано!")
        target = await db.get_user(target_id)
        await cb.message.edit_text(
            f"👤 <b>Баланс пополнен!</b>\nТеперь у {target['first_name']}: <b>{target['points']} фишек</b>",
            reply_markup=user_manage_kb(target_id, target)
        )

    elif action == "pts_sub":
        target_id = int(cb.data.split(":")[2])
        await db.spend_points(target_id, 100, reason="Списано админом")
        await cb.answer("-100 фишек списано!")
        target = await db.get_user(target_id)
        await cb.message.edit_text(
            f"👤 <b>Баланс изменен!</b>\nТеперь у {target['first_name']}: <b>{target['points']} фишек</b>",
            reply_markup=user_manage_kb(target_id, target)
        )

    elif action == "reset_chat":
        chat_id = cb.message.chat.id
        active = await db.get_active_session_in_chat(chat_id)
        if active:
            await db.cancel_session(active["id"])
            await cb.answer("Активная игра в чате сброшена!")
            await cb.message.answer(f"🛑 <b>Администратор принудительно сбросил игру #{active['id']} ({GAMES[active['game_type']]['name']}).</b>")
        else:
            await cb.answer("В этом чате нет зависших игр.", show_alert=True)
