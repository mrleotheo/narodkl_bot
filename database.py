import aiosqlite
import json

DB_PATH = "database.db"

async def init_db():
    """Инициализирует БД, создает новые таблицы и проводит безопасную миграцию."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                real_name TEXT,
                phone TEXT,
                utm_source TEXT,
                is_lead INTEGER DEFAULT 0,
                reminder_sent INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,     -- Поле активности
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Таблица прогревочных постов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS drip_posts (
                step_number INTEGER PRIMARY KEY,
                photo_id TEXT,
                text TEXT,
                buttons TEXT
            )
        """)
        # Таблица прогресса пользователей в воронке
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_drip_status (
                user_id INTEGER PRIMARY KEY,
                last_post_step INTEGER DEFAULT 0,
                last_sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Таблица администраторов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT
            )
        """)
        # Таблица черного списка (с поддержкой пустых ID для превентивного бана) [1.1.2]
        await db.execute("""
            CREATE TABLE IF NOT EXISTS blacklist (
                user_id INTEGER UNIQUE,
                username TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

        # Безопасная миграция для старых баз
        try:
            await db.execute("ALTER TABLE users ADD COLUMN reminder_sent INTEGER DEFAULT 1")
            await db.commit()
        except aiosqlite.OperationalError:
            pass

        try:
            await db.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
            await db.commit()
        except aiosqlite.OperationalError:
            pass

# --- ФУНКЦИИ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ---

async def add_user(user_id: int, username: str | None, first_name: str | None, last_name: str | None, utm_source: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (id, username, first_name, last_name, utm_source, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                is_active=1,
                utm_source=CASE WHEN users.utm_source IS NULL OR users.utm_source = 'direct' THEN excluded.utm_source ELSE users.utm_source END
        """, (user_id, username, first_name, last_name, utm_source))
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, username, first_name, last_name, utm_source, is_lead, real_name, phone, is_active FROM users WHERE id = ?", 
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "username": row[1],
                    "first_name": row[2],
                    "last_name": row[3],
                    "utm_source": row[4],
                    "is_lead": row[5],
                    "real_name": row[6],
                    "phone": row[7],
                    "is_active": row[8]
                }
            return None

async def update_user_active(user_id: int, is_active: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_active = ? WHERE id = ?", (is_active, user_id))
        await db.commit()

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_user_by_username(username: str):
    """Ищет пользователя в локальной базе по его юзернейму."""
    clean_username = username.lstrip("@").lower()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM users WHERE LOWER(username) = ?", (clean_username,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

# --- ФУНКЦИИ РАБОТЫ С ЧЕРНЫМ СПИСКОМ ---

async def add_to_blacklist(user_id: int | None, username: str | None):
    """Добавляет пользователя в черный список (поддерживает превентивный бан по нику) [1.1.2]."""
    clean_username = username.lstrip("@").lower() if username else None
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO blacklist (user_id, username) 
            VALUES (?, ?)
        """, (user_id, clean_username))
        await db.commit()

async def remove_from_blacklist(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM blacklist WHERE user_id = ?", (user_id,))
        await db.commit()

async def check_and_update_blacklist(user_id: int, username: str | None) -> bool:
    """
    Проверяет, заблокирован ли пользователь по ID или юзернейму.
    Если был превентивный бан по нику, автоматически привязывает его ID в базу [1.1.2]!
    """
    clean_username = username.lower() if username else None
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Проверяем блокировку по ID
        async with db.execute("SELECT 1 FROM blacklist WHERE user_id = ?", (user_id,)) as cursor:
            if await cursor.fetchone():
                return True
        
        # 2. Проверяем блокировку по никнейму (превентивную)
        if clean_username:
            async with db.execute("SELECT user_id FROM blacklist WHERE username = ?", (clean_username,)) as cursor:
                row = await cursor.fetchone()
                if row is not None:
                    # Если ID еще не был привязан (равен NULL), привязываем его! [1.1.2]
                    if row[0] is None:
                        await db.execute("UPDATE blacklist SET user_id = ? WHERE username = ?", (user_id, clean_username))
                        await db.commit()
                    return True
    return False

async def get_all_blacklisted():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, username FROM blacklist ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [{"user_id": r[0], "username": r[1]} for r in rows]

# --- ФУНКЦИИ РАБОТЫ С АДМИНИСТРАТОРАМИ ---

async def add_admin(user_id: int, username: str | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO admins (user_id, username) VALUES (?, ?)", (user_id, username))
        await db.commit()

async def del_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await db.commit()

async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone() is not None

async def get_all_admins():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM admins") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

# --- ФУНКЦИИ РАБОТЫ С ПОСТАМИ ВОРОНКИ ---

async def add_drip_post(photo_id: str | None, text: str, buttons: list | None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COALESCE(MAX(step_number), 0) FROM drip_posts") as cursor:
            row = await cursor.fetchone()
            next_step = row[0] + 1 if row else 1
        
        btn_json = json.dumps(buttons, ensure_ascii=False) if buttons else None
        await db.execute(
            "INSERT INTO drip_posts (step_number, photo_id, text, buttons) VALUES (?, ?, ?, ?)",
            (next_step, photo_id, text, btn_json)
        )
        await db.commit()

async def update_drip_post(step_number: int, photo_id: str | None, text: str, buttons: list | None):
    async with aiosqlite.connect(DB_PATH) as db:
        btn_json = json.dumps(buttons, ensure_ascii=False) if buttons else None
        await db.execute(
            "UPDATE drip_posts SET photo_id = ?, text = ?, buttons = ? WHERE step_number = ?",
            (photo_id, text, btn_json, step_number)
        )
        await db.commit()

async def get_all_drip_posts():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT step_number, photo_id, text, buttons FROM drip_posts ORDER BY step_number") as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "step_number": r[0],
                    "photo_id": r[1],
                    "text": r[2],
                    "buttons": json.loads(r[3]) if r[3] else None
                } for r in rows
            ]

async def get_drip_post(step_number: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT step_number, photo_id, text, buttons FROM drip_posts WHERE step_number = ?", (step_number,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "step_number": row[0],
                    "photo_id": row[1],
                    "text": row[2],
                    "buttons": json.loads(row[3]) if row[3] else None
                }
            return None

async def delete_drip_post(step_number: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM drip_posts WHERE step_number = ?", (step_number,))
        await db.execute("UPDATE drip_posts SET step_number = step_number - 1 WHERE step_number > ?", (step_number,))
        await db.execute("UPDATE user_drip_status SET last_post_step = last_post_step - 1 WHERE last_post_step >= ?", (step_number,))
        await db.commit()

# --- ФУНКЦИЯ ПОЛУЧЕНИЯ СТАТИСТИКИ ---

async def get_stats_data():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE is_active = 1") as cursor:
            active_users = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM blacklist") as cursor:
            banned_users = (await cursor.fetchone())[0]
            
        return {
            "total_users": total_users,
            "active_users": active_users,
            "banned_users": banned_users
        }