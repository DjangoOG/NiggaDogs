from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_menu():
    """Админ панель"""
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить категорию", callback_data="admin_add_category")],
        [InlineKeyboardButton(text="➕ Добавить подкатегорию", callback_data="admin_add_subcategory")],
        [InlineKeyboardButton(text="➕ Добавить пакет", callback_data="admin_add_package")],
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data="admin_edit")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data="admin_delete")],
        [InlineKeyboardButton(text="📎 Управление документами", callback_data="admin_manage_docs")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_emoji_keyboard():
    """Клавиатура выбора эмодзи"""
    keyboard = [
        [
            InlineKeyboardButton(text="📋", callback_data="emoji_📋"),
            InlineKeyboardButton(text="🏢", callback_data="emoji_🏢"),
            InlineKeyboardButton(text="👥", callback_data="emoji_👥"),
        ],
        [
            InlineKeyboardButton(text="📊", callback_data="emoji_📊"),
            InlineKeyboardButton(text="💼", callback_data="emoji_💼"),
            InlineKeyboardButton(text="📁", callback_data="emoji_📁"),
        ],
        [
            InlineKeyboardButton(text="📂", callback_data="emoji_📂"),
            InlineKeyboardButton(text="🗂", callback_data="emoji_🗂"),
            InlineKeyboardButton(text="📑", callback_data="emoji_📑"),
        ],
        [
            InlineKeyboardButton(text="📄", callback_data="emoji_📄"),
            InlineKeyboardButton(text="📝", callback_data="emoji_📝"),
            InlineKeyboardButton(text="🎯", callback_data="emoji_🎯"),
        ],
        [
            InlineKeyboardButton(text="⚙️", callback_data="emoji_⚙️"),
            InlineKeyboardButton(text="🔧", callback_data="emoji_🔧"),
            InlineKeyboardButton(text="🛠", callback_data="emoji_🛠"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)