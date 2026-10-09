"""Справочник игр, правил, эмодзи и очков в Telegram Dice."""

GAMES = {
    "dice": {
        "name": "Кубики",
        "emoji": "🎲",
        "dice_emoji": "🎲",
        "desc": "Бросок кости от 1 до 6. У кого больше очков — тот победил!",
        "max_score": 6,
    },
    "darts": {
        "name": "Дартс",
        "emoji": "🎯",
        "dice_emoji": "🎯",
        "desc": "Точность броска в мишень! Центр/яблочко = 6 очков.",
        "max_score": 6,
    },
    "basketball": {
        "name": "Баскетбол",
        "emoji": "🏀",
        "dice_emoji": "🏀",
        "desc": "Бросок в корзину! 4-5 очков = попадание!",
        "max_score": 5,
    },
    "football": {
        "name": "Футбол",
        "emoji": "⚽",
        "dice_emoji": "⚽",
        "desc": "Удар по воротам! 3, 4, 5 очков = ГОЛ!",
        "max_score": 5,
    },
    "bowling": {
        "name": "Боулинг / Кегли",
        "emoji": "🎳",
        "dice_emoji": "🎳",
        "desc": "Сбивание кеглей! 6 очков = СТРАЙК!",
        "max_score": 6,
    },
    "slots": {
        "name": "Казино / Слоты",
        "emoji": "🎰",
        "dice_emoji": "🎰",
        "desc": "Автомат 777! Три семерки (64 очка) = Джекпот!",
        "max_score": 64,
    },
    "roulette": {
        "name": "Колесо фортуны / Рулетка",
        "emoji": "🎡",
        "dice_emoji": None,
        "desc": "Случайный выбор победителя среди всех зарегистрировавшихся!",
        "max_score": 100,
    }
}

def format_dice_result(game_type: str, raw_value: int) -> tuple[int, str]:
    """Возвращает (очки_для_сравнения, текстовое_описание)."""
    if game_type == "basketball":
        # 4 и 5 - попадания
        if raw_value in (4, 5):
            return raw_value, "🎯 ТОЧНО В КОЛЬЦО!"
        elif raw_value == 3:
            return raw_value, "❌ Застрял на дужке!"
        else:
            return raw_value, "❌ Мимо щита!"
    elif game_type == "football":
        # 3, 4, 5 - голы
        if raw_value in (3, 4, 5):
            return raw_value, "⚽ ГОООЛ В ВОРОТА!"
        else:
            return raw_value, "❌ Мимо ворот / В штангу!"
    elif game_type == "bowling":
        if raw_value == 6:
            return raw_value, "🎳 СТРАЙК! Все кегли сбиты!"
        elif raw_value in (4, 5):
            return raw_value, f"🎳 Почти страйк! ({raw_value} кеглей)"
        elif raw_value in (2, 3):
            return raw_value, f"🎳 Сбито {raw_value} кегли."
        else:
            return raw_value, "❌ Шар ушёл в желоб!"
    elif game_type == "darts":
        if raw_value == 6:
            return raw_value, "🎯 В ЯБЛОЧКО! 100% точность!"
        elif raw_value == 5:
            return raw_value, "🎯 Красный сектор (рядом с центром)"
        else:
            return raw_value, f"🎯 Попадание ({raw_value} очк.)"
    elif game_type == "slots":
        if raw_value == 64:
            return raw_value, "🔥 СЕМЁРКИ 7-7-7! ДЖЕКПОТ!"
        elif raw_value in (1, 22, 43):
            return raw_value, f"🎰 Совпадение символов! ({raw_value})"
        else:
            return raw_value, f"🎰 Разброс ({raw_value})"
    else:  # dice or others
        return raw_value, f"Выпало {raw_value}"

