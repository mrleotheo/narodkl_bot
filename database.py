import aiosqlite
import os

DB_PATH = "database.db"

async def init_db():
    """Инициализирует БД и автоматически проводит миграцию для старых баз."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Создаем таблицу, если базы еще нет
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
        await db.commit()

        # Безопасная миграция для существующих баз данных [1.1.2]
        try:
            # Для старых пользователей ставим статус 1 (отправлено), чтобы уберечь их от спама [1.1.2].
            await db.execute("ALTER TABLE users ADD COLUMN reminder_sent INTEGER DEFAULT 1")
            await db.commit()
        except aiosqlite.OperationalError:
            # Если колонка уже есть, SQLite выдаст ошибку, мы ее просто игнорируем
            pass

async def add_user(user_id: int, username: str | None, first_name: str | None, last_name: str | None, utm_source: str):
    """Добавляет нового пользователя или обновляет данные существующего."""
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

async def get_all_users():
    """Возвращает ID всех зарегистрированных пользователей для рассылки."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]