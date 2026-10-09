"""Асинхронная база данных SQLite для игрового бота KazaGame."""
import os
from datetime import datetime
import aiosqlite
from config import DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    points INTEGER DEFAULT 100,
    wins INTEGER DEFAULT 0,
    games_played INTEGER DEFAULT 0,
    is_game_admin INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS game_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    game_type TEXT NOT NULL,
    status TEXT DEFAULT 'lobby', -- lobby, playing, finished, cancelled
    creator_id INTEGER NOT NULL,
    creator_name TEXT NOT NULL,
    bet INTEGER DEFAULT 0,
    target_players INTEGER DEFAULT 2,
    winner_id INTEGER DEFAULT NULL,
    winner_name TEXT DEFAULT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS session_players (
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    first_name TEXT NOT NULL,
    score INTEGER DEFAULT 0,
    dice_raw INTEGER DEFAULT 0,
    joined_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (session_id, user_id)
);

CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    game_type TEXT NOT NULL,
    players_count INTEGER NOT NULL,
    winner_name TEXT NOT NULL,
    winner_id INTEGER NOT NULL,
    bet INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS point_txs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
"""

def _connect():
    return aiosqlite.connect(DATABASE_PATH, timeout=30)

async def init_db():
    d = os.path.dirname(DATABASE_PATH)
    if d:
        os.makedirs(d, exist_ok=True)
    async with _connect() as db:
        await db.executescript(SCHEMA)
        await db.execute("PRAGMA journal_mode=WAL")
        await db.commit()

# --- Пользователи ---

async def get_user(user_id: int) -> dict | None:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

async def ensure_user(user_id: int, username: str | None, first_name: str) -> dict:
    async with _connect() as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name)
        )
        await db.execute(
            "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
            (username, first_name, user_id)
        )
        await db.commit()
    return await get_user(user_id)

async def update_user(user_id: int, **kwargs):
    if not kwargs:
        return
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    async with _connect() as db:
        await db.execute(f"UPDATE users SET {sets} WHERE user_id = ?", (*kwargs.values(), user_id))
        await db.commit()

async def add_points(user_id: int, amount: int, reason: str = ""):
    async with _connect() as db:
        await db.execute("UPDATE users SET points = MAX(0, points + ?) WHERE user_id = ?", (amount, user_id))
        await db.execute(
            "INSERT INTO point_txs (user_id, amount, reason) VALUES (?, ?, ?)",
            (user_id, amount, reason)
        )
        await db.commit()

async def spend_points(user_id: int, amount: int, reason: str = "") -> bool:
    if amount <= 0:
        return True
    async with _connect() as db:
        cur = await db.execute("UPDATE users SET points = points - ? WHERE user_id = ? AND points >= ?", (amount, user_id, amount))
        await db.commit()
        ok = cur.rowcount > 0
    if ok and reason:
        async with _connect() as db:
            await db.execute(
                "INSERT INTO point_txs (user_id, amount, reason) VALUES (?, ?, ?)",
                (user_id, -amount, reason)
            )
            await db.commit()
    return ok

async def get_user_by_username(username: str) -> dict | None:
    uname = username.lstrip("@").strip().lower()
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE LOWER(username) = ?", (uname,))
        row = await cur.fetchone()
        return dict(row) if row else None

async def search_users(query: str, limit: int = 15) -> list:
    q = query.lstrip("@").strip().lower()
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM users WHERE user_id = ? OR LOWER(username) LIKE ? OR LOWER(first_name) LIKE ? LIMIT ?",
            (int(q) if q.isdigit() else 0, f"%{q}%", f"%{q}%", limit)
        )
        return [dict(r) for r in await cur.fetchall()]

async def ensure_super_admins(admin_ids: list[int]):
    async with _connect() as db:
        for aid in admin_ids:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, first_name, is_game_admin) VALUES (?, ?, 1)",
                (aid, f"Admin_{aid}")
            )
            await db.execute(
                "UPDATE users SET is_game_admin = 1 WHERE user_id = ?",
                (aid,)
            )
        await db.commit()

async def get_all_users() -> list:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users ORDER BY points DESC")
        return [dict(r) for r in await cur.fetchall()]

async def get_game_admins() -> list:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE is_game_admin = 1")
        return [dict(r) for r in await cur.fetchall()]

async def get_top_players(limit: int = 10) -> list:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE is_banned = 0 ORDER BY wins DESC, points DESC LIMIT ?", (limit,))
        return [dict(r) for r in await cur.fetchall()]

# --- Игровые Сессии ---

async def create_session(chat_id: int, game_type: str, creator_id: int, creator_name: str, bet: int = 0, target_players: int = 2) -> int:
    async with _connect() as db:
        cur = await db.execute(
            "INSERT INTO game_sessions (chat_id, game_type, creator_id, creator_name, bet, target_players) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, game_type, creator_id, creator_name, bet, target_players)
        )
        sid = cur.lastrowid
        await db.execute(
            "INSERT INTO session_players (session_id, user_id, first_name) VALUES (?, ?, ?)",
            (sid, creator_id, creator_name)
        )
        await db.commit()
        return sid

async def get_session(session_id: int) -> dict | None:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM game_sessions WHERE id = ?", (session_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

async def get_active_session_in_chat(chat_id: int) -> dict | None:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM game_sessions WHERE chat_id = ? AND status IN ('lobby', 'playing') ORDER BY id DESC LIMIT 1",
            (chat_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None

async def join_session(session_id: int, user_id: int, first_name: str) -> bool:
    async with _connect() as db:
        try:
            await db.execute(
                "INSERT INTO session_players (session_id, user_id, first_name) VALUES (?, ?, ?)",
                (session_id, user_id, first_name)
            )
            await db.commit()
            return True
        except Exception:
            return False

async def get_session_players(session_id: int) -> list:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM session_players WHERE session_id = ? ORDER BY joined_at ASC", (session_id,))
        return [dict(r) for r in await cur.fetchall()]

async def update_player_score(session_id: int, user_id: int, score: int, raw: int):
    async with _connect() as db:
        await db.execute(
            "UPDATE session_players SET score = ?, dice_raw = ? WHERE session_id = ? AND user_id = ?",
            (score, raw, session_id, user_id)
        )
        await db.commit()

async def finish_session(session_id: int, winner_id: int, winner_name: str):
    async with _connect() as db:
        await db.execute(
            "UPDATE game_sessions SET status = 'finished', winner_id = ?, winner_name = ? WHERE id = ?",
            (winner_id, winner_name, session_id)
        )
        s = await (await db.execute("SELECT * FROM game_sessions WHERE id = ?", (session_id,))).fetchone()
        cnt = (await (await db.execute("SELECT COUNT(*) FROM session_players WHERE session_id = ?", (session_id,))).fetchone())[0]
        await db.execute(
            "INSERT INTO history (chat_id, game_type, players_count, winner_name, winner_id, bet) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (s[1], s[2], cnt, winner_name, winner_id, s[6])
        )
        # Обновим статистику победителя
        await db.execute("UPDATE users SET wins = wins + 1, games_played = games_played + 1 WHERE user_id = ?", (winner_id,))
        # Проигравшим обновим games_played
        await db.execute(
            "UPDATE users SET games_played = games_played + 1 WHERE user_id IN "
            "(SELECT user_id FROM session_players WHERE session_id = ? AND user_id != ?)",
            (session_id, winner_id)
        )
        await db.commit()

async def cancel_session(session_id: int):
    async with _connect() as db:
        await db.execute("UPDATE game_sessions SET status = 'cancelled' WHERE id = ?", (session_id,))
        await db.commit()

async def get_chat_history(chat_id: int, limit: int = 10) -> list:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM history WHERE chat_id = ? ORDER BY id DESC LIMIT ?", (chat_id, limit))
        return [dict(r) for r in await cur.fetchall()]

async def get_stats() -> dict:
    async with _connect() as db:
        async def val(q):
            return (await (await db.execute(q)).fetchone())[0] or 0
        return {
            "users": await val("SELECT COUNT(*) FROM users"),
            "games_total": await val("SELECT COUNT(*) FROM history"),
            "total_points": await val("SELECT SUM(points) FROM users"),
            "banned": await val("SELECT COUNT(*) FROM users WHERE is_banned = 1")
        }

