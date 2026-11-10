import aiosqlite
import time
from config import DB_PATH

# ---------- SCHEMA ----------
CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    joined_at INTEGER,
    is_banned INTEGER DEFAULT 0,
    is_premium INTEGER DEFAULT 0,
    downloads_today INTEGER DEFAULT 0,
    total_downloads INTEGER DEFAULT 0,
    last_reset_day TEXT
)
"""

CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
"""

CREATE_FORCE_JOIN = """
CREATE TABLE IF NOT EXISTS force_join_channels (
    chat_id TEXT PRIMARY KEY,
    title TEXT,
    invite_link TEXT
)
"""

CREATE_LOGS = """
CREATE TABLE IF NOT EXISTS download_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    platform TEXT,
    status TEXT,
    created_at INTEGER
)
"""

DEFAULT_SETTINGS = {
    "welcome_text": (
        "👋 <b>Welcome, {first_name}!</b>\n\n"
        "Send me any <b>YouTube / Instagram / TikTok / Twitter / Facebook</b> link "
        "and I'll download it for you in seconds. 🚀"
    ),
    "welcome_image": "",  # file_id, empty = no image
    "maintenance_mode": "0",
}


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_USERS)
        await db.execute(CREATE_SETTINGS)
        await db.execute(CREATE_FORCE_JOIN)
        await db.execute(CREATE_LOGS)
        for k, v in DEFAULT_SETTINGS.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
            )
        await db.commit()


# ---------- USERS ----------
async def add_user(user_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at, last_reset_day)
               VALUES (?, ?, ?, ?, date('now'))""",
            (user_id, username, first_name, int(time.time())),
        )
        await db.commit()


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cur.fetchone()


async def is_banned(user_id: int) -> bool:
    user = await get_user(user_id)
    return bool(user["is_banned"]) if user else False


async def set_ban(user_id: int, banned: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_banned = ? WHERE user_id = ?", (int(banned), user_id)
        )
        await db.commit()


async def set_premium(user_id: int, premium: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_premium = ? WHERE user_id = ?", (int(premium), user_id)
        )
        await db.commit()


async def reset_daily_if_needed(user_id: int):
    """Reset downloads_today counter if the stored day differs from today."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT last_reset_day FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cur.fetchone()
        if row is None:
            return
        cur2 = await db.execute("SELECT date('now') as today")
        today = (await cur2.fetchone())["today"]
        if row["last_reset_day"] != today:
            await db.execute(
                "UPDATE users SET downloads_today = 0, last_reset_day = ? WHERE user_id = ?",
                (today, user_id),
            )
            await db.commit()


async def increment_download_count(user_id: int, platform: str, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE users SET downloads_today = downloads_today + 1,
               total_downloads = total_downloads + 1 WHERE user_id = ?""",
            (user_id,),
        )
        await db.execute(
            "INSERT INTO download_logs (user_id, platform, status, created_at) VALUES (?, ?, ?, ?)",
            (user_id, platform, status, int(time.time())),
        )
        await db.commit()


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        total_users = (await (await db.execute("SELECT COUNT(*) c FROM users")).fetchone())["c"]
        today_users = (await (await db.execute(
            "SELECT COUNT(*) c FROM users WHERE date(joined_at, 'unixepoch') = date('now')"
        )).fetchone())["c"]
        total_downloads = (await (await db.execute(
            "SELECT COUNT(*) c FROM download_logs"
        )).fetchone())["c"]
        premium_users = (await (await db.execute(
            "SELECT COUNT(*) c FROM users WHERE is_premium = 1"
        )).fetchone())["c"]
        banned_users = (await (await db.execute(
            "SELECT COUNT(*) c FROM users WHERE is_banned = 1"
        )).fetchone())["c"]
        return {
            "total_users": total_users,
            "today_users": today_users,
            "total_downloads": total_downloads,
            "premium_users": premium_users,
            "banned_users": banned_users,
        }


async def get_all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE is_banned = 0")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


# ---------- SETTINGS ----------
async def get_setting(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cur.fetchone()
        return row[0] if row else ""


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()


# ---------- FORCE JOIN ----------
async def add_force_channel(chat_id: str, title: str, invite_link: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO force_join_channels (chat_id, title, invite_link) VALUES (?, ?, ?)",
            (chat_id, title, invite_link),
        )
        await db.commit()


async def remove_force_channel(chat_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM force_join_channels WHERE chat_id = ?", (chat_id,))
        await db.commit()


async def get_force_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM force_join_channels")
        return await cur.fetchall()
