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

def start_menu_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🎮 Выбрать игру", callback_data="gmenu")
    b.button(text="👤 Мой профиль", callback_data="uprofile")
    b.button(text="🏆 Топ игроков", callback_data="utop")
    b.button(text="❓ Как играть", callback_data="uhelp")
    if is_admin:
        b.button(text="👑 Админ-панель", callback_data="adm:main")
    b.adjust(2, 2, 1)
    return b.as_markup()

def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="➕ Добавить админа", callback_data="adm:add_admin"), Btn(text="👑 Список админов", callback_data="adm:admins")],
        [Btn(text="👥 Список игроков", callback_data="adm:users:0"), Btn(text="🔍 Найти игрока", callback_data="adm:search_user")],
        [Btn(text="🎲 Запуск игры (админ)", callback_data="adm:game_pick"), Btn(text="🛑 Сброс игры в чате", callback_data="adm:reset_chat")],
        [Btn(text="📊 Статистика бота", callback_data="adm:stats"), Btn(text="📢 Рассылка игрокам", callback_data="adm:broadcast")],
        [Btn(text="✖️ Закрыть панель", callback_data="adm:close")]
    ])

def admin_game_pick_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for k, g in GAMES.items():
        b.button(text=f"{g['emoji']} {g['name']}", callback_data=f"gstart:{k}")
    b.adjust(2)
    b.row(Btn(text="◀️ Назад в админку", callback_data="adm:main"))
    return b.as_markup()

def user_manage_kb(uid: int, u: dict) -> InlineKeyboardMarkup:
    adm_text = "👤 Снять права админа" if u.get("is_game_admin") else "👑 Сделать админом игр"
    ban_text = "✅ Разбанить" if u.get("is_banned") else "🚫 Забанить"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            Btn(text="💰 +100", callback_data=f"adm:pts_add:{uid}:100"),
            Btn(text="💰 +500", callback_data=f"adm:pts_add:{uid}:500"),
            Btn(text="💸 -100", callback_data=f"adm:pts_sub:{uid}:100")
        ],
        [Btn(text=adm_text, callback_data=f"adm:toggle_adm:{uid}")],
        [Btn(text=ban_text, callback_data=f"adm:toggle_ban:{uid}")],
        [Btn(text="◀️ Назад к игрокам", callback_data="adm:users:0")]
    ])

def back_kb(cb: str = "adm:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[Btn(text="◀️ Назад", callback_data=cb)]])

def cancel_fsm_kb(cb: str = "adm:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[Btn(text="❌ Отмена", callback_data=cb)]])
