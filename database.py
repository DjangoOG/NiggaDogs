import aiosqlite
from config import DATABASE_PATH

class Database:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
    
    async def get_root_categories(self):
        """Получить корневые категории"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, name, emoji FROM Categories "
                "WHERE parent_id IS NULL ORDER BY order_index"
            )
            return await cursor.fetchall()
    
    async def get_subcategories(self, parent_id: int):
        """Получить подкатегории"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, name, emoji FROM Categories "
                "WHERE parent_id = ? ORDER BY order_index",
                (parent_id,)
            )
            return await cursor.fetchall()
    
    async def get_packages(self, category_id: int):
        """Получить пакеты в категории"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, name, description FROM Packages "
                "WHERE category_id = ? ORDER BY order_index",
                (category_id,)
            )
            return await cursor.fetchall()
    
    async def get_category_info(self, category_id: int):
        """Получить информацию о категории"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT name, emoji, description, parent_id FROM Categories WHERE id = ?",
                (category_id,)
            )
            row = await cursor.fetchone()
            if row:
                return {
                    'name': row[0],
                    'emoji': row[1],
                    'description': row[2],
                    'parent_id': row[3]
                }
            return None
    
    async def get_package_info(self, package_id: int):
        """Получить информацию о пакете"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT name, description, category_id FROM Packages WHERE id = ?",
                (package_id,)
            )
            row = await cursor.fetchone()
            if row:
                return {
                    'name': row[0],
                    'description': row[1],
                    'category_id': row[2]
                }
            return None
    
    async def get_package_documents(self, package_id: int):
        """Получить документы пакета"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, filename, file_path, file_id FROM Documents "
                "WHERE package_id = ? ORDER BY filename",
                (package_id,)
            )
            rows = await cursor.fetchall()
            return [{'id': r[0], 'filename': r[1], 'file_path': r[2], 'file_id': r[3]} for r in rows]
    
    async def get_document_info(self, doc_id: int):
        """Получить информацию о документе"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT filename, file_path, file_id FROM Documents WHERE id = ?",
                (doc_id,)
            )
            row = await cursor.fetchone()
            if row:
                return {
                    'filename': row[0],
                    'file_path': row[1],
                    'file_id': row[2]
                }
            return None
    
    async def has_subcategories(self, category_id: int) -> bool:
        """Проверить есть ли подкатегории"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM Categories WHERE parent_id = ?",
                (category_id,)
            )
            count = await cursor.fetchone()
            return count[0] > 0
    
    async def has_packages(self, category_id: int) -> bool:
        """Проверить есть ли пакеты"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM Packages WHERE category_id = ?",
                (category_id,)
            )
            count = await cursor.fetchone()
            return count[0] > 0
    
    async def create_category(self, name: str, emoji: str, parent_id=None, description=None):
        """Создать категорию"""
        async with aiosqlite.connect(self.db_path) as db:
            level = 0
            if parent_id:
                cursor = await db.execute("SELECT level FROM Categories WHERE id = ?", (parent_id,))
                row = await cursor.fetchone()
                if row:
                    level = row[0] + 1
            
            cursor = await db.execute(
                "INSERT INTO Categories (name, emoji, parent_id, level, description) VALUES (?, ?, ?, ?, ?)",
                (name, emoji, parent_id, level, description)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def create_package(self, category_id: int, name: str, description=None):
        """Создать пакет"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO Packages (category_id, name, description) VALUES (?, ?, ?)",
                (category_id, name, description)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def create_document(self, package_id: int, filename: str, file_path: str, 
                            file_type: str, file_id: str, file_size: int):
        """Создать документ"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO Documents (package_id, filename, file_path, file_type, file_id, file_size) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (package_id, filename, file_path, file_type, file_id, file_size)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def update_document_file_id(self, doc_id: int, file_id: str):
        """Обновить file_id документа"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE Documents SET file_id = ? WHERE id = ?",
                (file_id, doc_id)
            )
            await db.commit()
    
    async def get_category_path(self, category_id: int) -> list:
        """Получить полный путь к категории"""
        path = []
        current_id = category_id

        async with aiosqlite.connect(self.db_path) as db:
            while current_id:
                cursor = await db.execute(
                    "SELECT name, emoji, parent_id FROM Categories WHERE id = ?",
                    (current_id,)
                )
                row = await cursor.fetchone()
                if row:
                    path.insert(0, f"{row[1]} {row[0]}")
                    current_id = row[2]
                else:
                    break

        return path

    async def delete_category(self, category_id: int):
        """Удалить категорию (и все вложенные подкатегории/пакеты)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM Categories WHERE id = ?", (category_id,))
            await db.commit()

    async def delete_package(self, package_id: int):
        """Удалить пакет (и все его документы)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM Packages WHERE id = ?", (package_id,))
            await db.commit()

    async def delete_document(self, doc_id: int):
        """Удалить документ"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM Documents WHERE id = ?", (doc_id,))
            await db.commit()

    async def get_all_packages(self):
        """Получить все пакеты со своими категориями"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT p.id, p.name, c.name, c.emoji
                FROM Packages p
                JOIN Categories c ON p.category_id = c.id
                ORDER BY c.name, p.name
            """)
            return await cursor.fetchall()

    async def get_all_categories_with_subcategories(self):
        """Получить все категории с подкатегориями"""
        all_categories = []

        async with aiosqlite.connect(self.db_path) as db:
            # Сначала корневые
            root_cats = await self.get_root_categories()
            for cat_id, name, emoji in root_cats:
                all_categories.append((cat_id, name, emoji, 0))

                # Потом их подкатегории
                subcats = await self.get_subcategories(cat_id)
                for sub_id, sub_name, sub_emoji in subcats:
                    all_categories.append((sub_id, sub_name, sub_emoji, 1))

        return all_categories