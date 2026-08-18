import aiosqlite

DB_PATH = "database.db"

async def init_db():
    """Создает таблицу пользователей с новыми полями."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                real_name TEXT,          -- Реальное имя из формы
                phone TEXT,              -- Номер телефона из формы
                utm_source TEXT,
                is_lead INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def add_user(user_id: int, username: str | None, first_name: str | None, last_name: str | None, utm_source: str):
    """Добавляет пользователя при старте."""
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
    """Получает информацию о пользователе."""
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

async def save_lead_data(user_id: int, real_name: str, phone: str):
    """Сохраняет контакты и помечает пользователя как лида."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET real_name = ?, phone = ?, is_lead = 1 WHERE id = ?", 
            (real_name, phone, user_id)
        )
        await db.commit()