import asyncio
import aiosqlite
import sys

print("🔄 Начинаю инициализацию базы данных...")

async def init_database():
    try:
        print("📂 Подключаюсь к базе данных...")
        async with aiosqlite.connect('bot.db') as db:
            print("📝 Создаю таблицу Categories...")
            await db.execute('''
                CREATE TABLE IF NOT EXISTS Categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    emoji TEXT DEFAULT '📁',
                    parent_id INTEGER,
                    level INTEGER DEFAULT 0,
                    description TEXT,
                    order_index INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_id) REFERENCES Categories(id) ON DELETE CASCADE
                )
            ''')
            
            print("📝 Создаю таблицу Packages...")
            await db.execute('''
                CREATE TABLE IF NOT EXISTS Packages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    order_index INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES Categories(id) ON DELETE CASCADE
                )
            ''')
            
            print("📝 Создаю таблицу Documents...")
            await db.execute('''
                CREATE TABLE IF NOT EXISTS Documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT,
                    file_id TEXT,
                    file_size INTEGER,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (package_id) REFERENCES Packages(id) ON DELETE CASCADE
                )
            ''')
            
            print("💾 Сохраняю изменения...")
            await db.commit()
            print("✅ База данных успешно инициализирована!")
            print("📁 Файл bot.db создан в текущей директории")
    except Exception as e:
        print(f"❌ Ошибка при создании базы данных: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(init_database())
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)