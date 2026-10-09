"""Клавиатуры для лобби игр, админки и профиля."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn
from aiogram.utils.keyboard import InlineKeyboardBuilder
from games import GAMES

def game_select_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for k, g in GAMES.items():
        b.button(text=f"{g['emoji']} {g['name']}", callback_data=f"gstart:{k}")
    b.adjust(2)
    return b.as_markup()

def lobby_kb(session_id: int, current_count: int, target_count: int, can_start_early: bool = True) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✋ Присоединиться к игре", callback_data=f"gjoin:{session_id}")
    if can_start_early and current_count >= 2:
        b.button(text=f"🟢 Начать броски ({current_count})", callback_data=f"gplay:{session_id}")
    b.button(text="❌ Отменить (создатель/админ)", callback_data=f"gcancel:{session_id}")
    b.adjust(1)
    return b.as_markup()

def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="📊 Статистика", callback_data="adm:stats"), Btn(text="👥 Игроки", callback_data="adm:users:0")],
        [Btn(text="👑 Список игровых админов", callback_data="adm:admins"), Btn(text="🎲 Запустить игру от админа", callback_data="adm:game_pick")],
        [Btn(text="🛑 Сбросить активную игру в чате", callback_data="adm:reset_chat")],
        [Btn(text="✖️ Закрыть", callback_data="adm:close")]
    ])

def user_manage_kb(uid: int, u: dict) -> InlineKeyboardMarkup:
    adm_text = "👤 Снять права админа" if u.get("is_game_admin") else "👑 Сделать админом игр"
    ban_text = "✅ Разбанить" if u.get("is_banned") else "🚫 Забанить"
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="💰 +100 фишек", callback_data=f"adm:pts_add:{uid}"), Btn(text="💸 -100 фишек", callback_data=f"adm:pts_sub:{uid}")],
        [Btn(text=adm_text, callback_data=f"adm:toggle_adm:{uid}")],
        [Btn(text=ban_text, callback_data=f"adm:toggle_ban:{uid}")],
        [Btn(text="◀️ Назад к игрокам", callback_data="adm:users:0")]
    ])

def back_kb(cb: str = "adm:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[Btn(text="◀️ Назад", callback_data=cb)]])
