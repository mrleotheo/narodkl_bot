import aiosqlite
import json

DB_PATH = "database.db"

async def init_db():
    """Инициализирует БД и автоматически проводит миграцию."""
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
        await db.commit()

        # Безопасная миграция для старых баз
        try:
            await db.execute("ALTER TABLE users ADD COLUMN reminder_sent INTEGER DEFAULT 1")
            await db.commit()
        except aiosqlite.OperationalError:
            pass

# --- ФУНКЦИИ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ---

async def add_user(user_id: int, username: str | None, first_name: str | None, last_name: str | None, utm_source: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (id, username, first_name, last_name, utm_source)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                utm_source=CASE WHEN users.utm_source IS NULL OR users.utm_source = 'direct' THEN excluded.utm_source ELSE users.utm_source END
        """, (user_id, username, first_name, last_name, utm_source))
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, username, first_name, last_name, utm_source, is_lead, real_name, phone FROM users WHERE id = ?", 
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
                    "phone": row[7]
                }
            return None

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

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
    """Удаляет пост и автоматически переиндексирует последующие шаги."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM drip_posts WHERE step_number = ?", (step_number,))
        # Сдвигаем все последующие шаги на один назад [1.1.2]
        await db.execute("UPDATE drip_posts SET step_number = step_number - 1 WHERE step_number > ?", (step_number,))
        # Также сдвигаем прогресс пользователей, чтобы они не зависли [1.1.2]
        await db.execute("UPDATE user_drip_status SET last_post_step = last_post_step - 1 WHERE last_post_step >= ?", (step_number,))
        await db.commit()