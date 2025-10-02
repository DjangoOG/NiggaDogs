from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import Database

db = Database()

async def get_main_menu():
    """Главное меню - корневые категории"""
    categories = await db.get_root_categories()
    
    keyboard = []
    row = []
    for cat_id, name, emoji in categories:
        button = InlineKeyboardButton(
            text=f"{emoji} {name}",
            callback_data=f"cat_{cat_id}"
        )
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def get_category_content(category_id: int, parent_id=None):
    """Контент категории - подкатегории и пакеты"""
    subcategories = await db.get_subcategories(category_id)
    packages = await db.get_packages(category_id)
    
    keyboard = []
    
    # Добавляем подкатегории
    row = []
    for subcat_id, name, emoji in subcategories:
        button = InlineKeyboardButton(
            text=f"{emoji} {name}",
            callback_data=f"cat_{subcat_id}"
        )
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Добавляем пакеты
    row = []
    for pack_id, name, _ in packages:
        button = InlineKeyboardButton(
            text=f"📦 {name}",
            callback_data=f"pack_{pack_id}"
        )
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Кнопки навигации
    nav_row = []
    
    if parent_id:
        nav_row.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"cat_{parent_id}"
        ))
    
    nav_row.append(InlineKeyboardButton(
        text="🏠 Главное меню",
        callback_data="main_menu"
    ))
    
    keyboard.append(nav_row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def get_package_keyboard(package_id: int, category_id: int):
    """Клавиатура для пакета с документами"""
    documents = await db.get_package_documents(package_id)
    
    keyboard = []
    for doc in documents:
        keyboard.append([InlineKeyboardButton(
            text=f"📄 {doc['filename']}",
            callback_data=f"doc_{doc['id']}"
        )])
    
    # Навигация
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"cat_{category_id}"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)