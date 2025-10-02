from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
import aiosqlite

from keyboards.admin_kb import get_admin_menu, get_emoji_keyboard
from keyboards.user_kb import get_main_menu
from database import Database
from config import ADMIN_IDS, DOCUMENTS_PATH, DATABASE_PATH

router = Router()
db = Database()

# FSM States

class DeleteStates(StatesGroup):
    choosing_what_to_delete = State()
    choosing_category = State()
    choosing_package = State()
    confirming_deletion = State()
class AddCategoryStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_emoji = State()

class AddSubcategoryStates(StatesGroup):
    choosing_parent = State()
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_emoji = State()

class AddPackageStates(StatesGroup):
    choosing_category = State()
    waiting_for_name = State()
    waiting_for_description = State()
    uploading_files = State()

class EditStates(StatesGroup):
    choosing_what_to_edit = State()
    choosing_category = State()
    choosing_package = State()
    entering_new_name = State()
    entering_new_description = State()
class DeleteStates(StatesGroup):
    choosing_what_to_delete = State()
    choosing_category = State()
    choosing_package = State()
    confirming_deletion = State()
# Проверка админа
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# Команды админа
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Эта команда доступна только администраторам")
        return
    
    await message.answer(
        "🔧 Админ-панель\n"
        "Выберите действие:",
        reply_markup=get_admin_menu()
    )

@router.callback_query(F.data == "admin_close")
async def close_admin(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    await callback.message.delete()
    await callback.answer()

# === ДОБАВЛЕНИЕ КАТЕГОРИИ ===

@router.callback_query(F.data == "admin_add_category")
async def start_add_category(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    await callback.message.answer("Введите название категории:")
    await state.set_state(AddCategoryStates.waiting_for_name)
    await callback.answer()

@router.message(AddCategoryStates.waiting_for_name)
async def process_category_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите описание категории (или /skip чтобы пропустить):")
    await state.set_state(AddCategoryStates.waiting_for_description)

@router.message(AddCategoryStates.waiting_for_description)
async def process_category_description(message: Message, state: FSMContext):
    if message.text != "/skip":
        await state.update_data(description=message.text)
    
    await message.answer(
        "Выберите эмодзи для категории:",
        reply_markup=get_emoji_keyboard()
    )
    await state.set_state(AddCategoryStates.waiting_for_emoji)

@router.callback_query(AddCategoryStates.waiting_for_emoji, F.data.startswith("emoji_"))
async def process_category_emoji(callback: CallbackQuery, state: FSMContext):
    emoji = callback.data.replace("emoji_", "")
    
    # Сохраняем эмодзи и создаем категорию
    data = await state.get_data()
    
    category_id = await db.create_category(
        name=data['name'],
        emoji=emoji,
        description=data.get('description'),
        parent_id=None
    )
    
    await callback.message.answer(
        f"✅ Категория '{emoji} {data['name']}' успешно создана!"
    )
    
    await state.clear()
    await callback.answer()

# === ДОБАВЛЕНИЕ ПОДКАТЕГОРИИ ===

@router.callback_query(F.data == "admin_add_subcategory")
async def start_add_subcategory(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    categories = await db.get_root_categories()
    
    if not categories:
        await callback.message.answer("❌ Сначала создайте хотя бы одну категорию!")
        await callback.answer()
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = []
    for cat_id, name, emoji in categories:
        keyboard.append([InlineKeyboardButton(
            text=f"{emoji} {name}",
            callback_data=f"addsubcat_parent_{cat_id}"
        )])
    
    await callback.message.answer(
        "Выберите родительскую категорию:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AddSubcategoryStates.choosing_parent)
    await callback.answer()

@router.callback_query(AddSubcategoryStates.choosing_parent, F.data.startswith("addsubcat_parent_"))
async def process_subcategory_parent(callback: CallbackQuery, state: FSMContext):
    parent_id = int(callback.data.split("_")[2])
    await state.update_data(parent_id=parent_id)
    
    cat_info = await db.get_category_info(parent_id)
    
    await callback.message.answer(
        f"Вы создаете подкатегорию внутри '{cat_info['emoji']} {cat_info['name']}'\n"
        f"Введите название подкатегории:"
    )
    await state.set_state(AddSubcategoryStates.waiting_for_name)
    await callback.answer()

@router.message(AddSubcategoryStates.waiting_for_name)
async def process_subcategory_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите описание подкатегории (или /skip):")
    await state.set_state(AddSubcategoryStates.waiting_for_description)

@router.message(AddSubcategoryStates.waiting_for_description)
async def process_subcategory_description(message: Message, state: FSMContext):
    if message.text != "/skip":
        await state.update_data(description=message.text)
    
    await message.answer(
        "Выберите эмодзи для подкатегории:",
        reply_markup=get_emoji_keyboard()
    )
    await state.set_state(AddSubcategoryStates.waiting_for_emoji)

@router.callback_query(AddSubcategoryStates.waiting_for_emoji, F.data.startswith("emoji_"))
async def process_subcategory_emoji(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    # Проверяем, это создание подкатегории или редактирование
    if 'parent_id' in data:
        emoji = callback.data.replace("emoji_", "")
        
        category_id = await db.create_category(
            name=data['name'],
            emoji=emoji,
            description=data.get('description'),
            parent_id=data['parent_id']
        )
        
        parent_info = await db.get_category_info(data['parent_id'])
        
        await callback.message.answer(
            f"✅ Подкатегория '{emoji} {data['name']}' создана внутри "
            f"'{parent_info['emoji']} {parent_info['name']}'!"
        )
        
        await state.clear()
        await callback.answer()

# === ДОБАВЛЕНИЕ ПАКЕТА ===

@router.callback_query(F.data == "admin_add_package")
async def start_add_package(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    categories = await db.get_root_categories()
    
    if not categories:
        await callback.message.answer("❌ Сначала создайте хотя бы одну категорию!")
        await callback.answer()
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = []
    for cat_id, name, emoji in categories:
        keyboard.append([InlineKeyboardButton(
            text=f"{emoji} {name}",
            callback_data=f"addpack_cat_{cat_id}"
        )])
    
    await callback.message.answer(
        "Выберите категорию для пакета:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(AddPackageStates.choosing_category)
    await callback.answer()

@router.callback_query(AddPackageStates.choosing_category, F.data.startswith("addpack_cat_"))
async def process_package_category(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[2])
    
    # Проверяем есть ли подкатегории
    subcategories = await db.get_subcategories(category_id)
    
    if subcategories:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = []
        
        for subcat_id, name, emoji in subcategories:
            keyboard.append([InlineKeyboardButton(
                text=f"{emoji} {name}",
                callback_data=f"addpack_cat_{subcat_id}"
            )])
        
        cat_info = await db.get_category_info(category_id)
        keyboard.append([InlineKeyboardButton(
            text=f"⬆️ Создать пакет в '{cat_info['name']}'",
            callback_data=f"addpack_here_{category_id}"
        )])
        
        await callback.message.edit_text(
            "Выберите подкатегорию или создайте пакет здесь:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    else:
        await state.update_data(category_id=category_id)
        path = await db.get_category_path(category_id)
        path_text = " → ".join(path)
        
        await callback.message.answer(
            f"Вы создаете пакет в категории:\n{path_text}\n\n"
            f"Введите название пакета:"
        )
        await state.set_state(AddPackageStates.waiting_for_name)
    
    await callback.answer()

@router.callback_query(F.data.startswith("addpack_here_"))
async def create_package_here(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[2])
    await state.update_data(category_id=category_id)
    
    path = await db.get_category_path(category_id)
    path_text = " → ".join(path)
    
    await callback.message.answer(
        f"Вы создаете пакет в категории:\n{path_text}\n\n"
        f"Введите название пакета:"
    )
    await state.set_state(AddPackageStates.waiting_for_name)
    await callback.answer()

@router.message(AddPackageStates.waiting_for_name)
async def process_package_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите описание пакета (или /skip):")
    await state.set_state(AddPackageStates.waiting_for_description)

@router.message(AddPackageStates.waiting_for_description)
async def process_package_description(message: Message, state: FSMContext):
    if message.text != "/skip":
        await state.update_data(description=message.text)
    
    await message.answer(
        "📎 Отправьте документы для пакета (можно отправить несколько).\n"
        "Когда закончите, напишите /done"
    )
    await state.update_data(files=[])
    await state.set_state(AddPackageStates.uploading_files)

@router.message(AddPackageStates.uploading_files, F.document)
async def process_package_files(message: Message, state: FSMContext, bot: Bot):
    file_id = message.document.file_id
    file_name = message.document.file_name
    file_size = message.document.file_size
    
    # Проверка размера
    if file_size > 50 * 1024 * 1024:
        await message.answer("❌ Файл слишком большой (максимум 50 MB)")
        return
    
    # Скачиваем файл
    file = await bot.get_file(file_id)
    file_path = f"{DOCUMENTS_PATH}/{file_id}_{file_name}"
    
    os.makedirs(DOCUMENTS_PATH, exist_ok=True)
    await bot.download_file(file.file_path, file_path)
    
    # Добавляем в список
    data = await state.get_data()
    files = data.get('files', [])
    files.append({
        'file_id': file_id,
        'filename': file_name,
        'file_path': file_path,
        'file_size': file_size,
        'file_type': file_name.split('.')[-1] if '.' in file_name else ''
    })
    await state.update_data(files=files)
    
    await message.answer(
        f"✅ Файл '{file_name}' сохранен.\n"
        f"Всего файлов: {len(files)}\n\n"
        f"Отправьте еще или напишите /done"
    )

@router.message(AddPackageStates.uploading_files, Command("done"))
async def finish_package_creation(message: Message, state: FSMContext):
    data = await state.get_data()
    files = data.get('files', [])
    
    if not files:
        await message.answer("❌ Вы не загрузили ни одного файла!")
        return
    
    # Создаем пакет
    package_id = await db.create_package(
        category_id=data['category_id'],
        name=data['name'],
        description=data.get('description')
    )
    
    # Добавляем документы
    for file_info in files:
        await db.create_document(
            package_id=package_id,
            filename=file_info['filename'],
            file_path=file_info['file_path'],
            file_type=file_info['file_type'],
            file_id=file_info['file_id'],
            file_size=file_info['file_size']
        )
    
    path = await db.get_category_path(data['category_id'])
    path_text = " → ".join(path)
    
    await message.answer(
        f"✅ Пакет '{data['name']}' создан с {len(files)} документами!\n\n"
        f"Путь: {path_text} → {data['name']}"
    )
    
    await state.clear()

# === РЕДАКТИРОВАНИЕ ===

@router.callback_query(F.data == "admin_edit")
async def start_edit(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = [
        [InlineKeyboardButton(text="✏️ Редактировать категорию", callback_data="edit_category")],
        [InlineKeyboardButton(text="✏️ Редактировать пакет", callback_data="edit_package")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
    ]
    
    await callback.message.edit_text(
        "Что хотите отредактировать?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

# === РЕДАКТИРОВАНИЕ КАТЕГОРИИ ===

@router.callback_query(F.data == "edit_category")
async def choose_category_to_edit(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    # Получаем все категории (и корневые и подкатегории)
    all_categories = []
    
    # Сначала корневые
    root_cats = await db.get_root_categories()
    for cat_id, name, emoji in root_cats:
        all_categories.append((cat_id, name, emoji, 0))
        
        # Потом их подкатегории
        subcats = await db.get_subcategories(cat_id)
        for sub_id, sub_name, sub_emoji in subcats:
            all_categories.append((sub_id, sub_name, sub_emoji, 1))
    
    if not all_categories:
        await callback.message.answer("❌ Нет категорий для редактирования!")
        await callback.answer()
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = []
    
    for cat_id, name, emoji, level in all_categories:
        prefix = "  " * level  # Отступ для подкатегорий
        keyboard.append([InlineKeyboardButton(
            text=f"{prefix}{emoji} {name}",
            callback_data=f"editcat_{cat_id}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")])
    
    await callback.message.edit_text(
        "Выберите категорию для редактирования:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(EditStates.choosing_category)
    await callback.answer()

@router.callback_query(EditStates.choosing_category, F.data.startswith("editcat_"))
async def edit_category_menu(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[1])
    await state.update_data(category_id=category_id)
    
    cat_info = await db.get_category_info(category_id)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = [
        [InlineKeyboardButton(text="✏️ Изменить название", callback_data="editcat_name")],
        [InlineKeyboardButton(text="📝 Изменить описание", callback_data="editcat_desc")],
        [InlineKeyboardButton(text="🎨 Изменить эмодзи", callback_data="editcat_emoji")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
    ]
    
    desc_text = cat_info['description'] if cat_info['description'] else "нет"
    
    await callback.message.edit_text(
        f"Редактирование категории:\n"
        f"{cat_info['emoji']} {cat_info['name']}\n\n"
        f"Описание: {desc_text}\n\n"
        f"Что изменить?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "editcat_name")
async def edit_category_name_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое название категории:")
    await state.set_state(EditStates.entering_new_name)
    await state.update_data(edit_type="category_name")
    await callback.answer()

@router.message(EditStates.entering_new_name)
async def process_new_name(message: Message, state: FSMContext):
    data = await state.get_data()
    
    if data.get('edit_type') == "category_name":
        async with aiosqlite.connect(DATABASE_PATH) as db_conn:
            await db_conn.execute(
                "UPDATE Categories SET name = ? WHERE id = ?",
                (message.text, data['category_id'])
            )
            await db_conn.commit()
        
        await message.answer(f"✅ Название категории изменено на '{message.text}'!")
        await state.clear()
    
    elif data.get('edit_type') == "package_name":
        async with aiosqlite.connect(DATABASE_PATH) as db_conn:
            await db_conn.execute(
                "UPDATE Packages SET name = ? WHERE id = ?",
                (message.text, data['package_id'])
            )
            await db_conn.commit()
        
        await message.answer(f"✅ Название пакета изменено на '{message.text}'!")
        await state.clear()

@router.callback_query(F.data == "editcat_desc")
async def edit_category_desc_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое описание категории (или /skip чтобы удалить):")
    await state.set_state(EditStates.entering_new_description)
    await state.update_data(edit_type="category_desc")
    await callback.answer()

@router.message(EditStates.entering_new_description)
async def process_new_description(message: Message, state: FSMContext):
    data = await state.get_data()
    new_desc = None if message.text == "/skip" else message.text
    
    if data.get('edit_type') == "category_desc":
        async with aiosqlite.connect(DATABASE_PATH) as db_conn:
            await db_conn.execute(
                "UPDATE Categories SET description = ? WHERE id = ?",
                (new_desc, data['category_id'])
            )
            await db_conn.commit()
        
        if new_desc:
            await message.answer(f"✅ Описание категории изменено!")
        else:
            await message.answer(f"✅ Описание категории удалено!")
        await state.clear()
    
    elif data.get('edit_type') == "package_desc":
        async with aiosqlite.connect(DATABASE_PATH) as db_conn:
            await db_conn.execute(
                "UPDATE Packages SET description = ? WHERE id = ?",
                (new_desc, data['package_id'])
            )
            await db_conn.commit()
        
        if new_desc:
            await message.answer(f"✅ Описание пакета изменено!")
        else:
            await message.answer(f"✅ Описание пакета удалено!")
        await state.clear()

@router.callback_query(F.data == "editcat_emoji")
async def edit_category_emoji_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Выберите новый эмодзи для категории:",
        reply_markup=get_emoji_keyboard()
    )
    await state.update_data(edit_type="category_emoji")
    await callback.answer()

# === РЕДАКТИРОВАНИЕ ПАКЕТА ===

@router.callback_query(F.data == "edit_package")
async def choose_package_to_edit(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    # Получаем все пакеты из всех категорий
    all_packages = []
    
    async with aiosqlite.connect(DATABASE_PATH) as db_conn:
        cursor = await db_conn.execute("""
            SELECT p.id, p.name, c.name, c.emoji 
            FROM Packages p
            JOIN Categories c ON p.category_id = c.id
            ORDER BY c.name, p.name
        """)
        rows = await cursor.fetchall()
        for row in rows:
            all_packages.append(row)
    
    if not all_packages:
        await callback.message.answer("❌ Нет пакетов для редактирования!")
        await callback.answer()
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = []
    
    for pack_id, pack_name, cat_name, cat_emoji in all_packages:
        keyboard.append([InlineKeyboardButton(
            text=f"📦 {pack_name} (в {cat_emoji} {cat_name})",
            callback_data=f"editpack_{pack_id}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")])
    
    await callback.message.edit_text(
        "Выберите пакет для редактирования:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(EditStates.choosing_package)
    await callback.answer()

@router.callback_query(EditStates.choosing_package, F.data.startswith("editpack_"))
async def edit_package_menu(callback: CallbackQuery, state: FSMContext):
    package_id = int(callback.data.split("_")[1])
    await state.update_data(package_id=package_id)
    
    pack_info = await db.get_package_info(package_id)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = [
        [InlineKeyboardButton(text="✏️ Изменить название", callback_data="editpack_name")],
        [InlineKeyboardButton(text="📝 Изменить описание", callback_data="editpack_desc")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
    ]
    
    desc_text = pack_info['description'] if pack_info['description'] else "нет"
    
    await callback.message.edit_text(
        f"Редактирование пакета:\n"
        f"📦 {pack_info['name']}\n\n"
        f"Описание: {desc_text}\n\n"
        f"Что изменить?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "editpack_name")
async def edit_package_name_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое название пакета:")
    await state.set_state(EditStates.entering_new_name)
    await state.update_data(edit_type="package_name")
    await callback.answer()

@router.callback_query(F.data == "editpack_desc")
async def edit_package_desc_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое описание пакета (или /skip чтобы удалить):")
    await state.set_state(EditStates.entering_new_description)
    await state.update_data(edit_type="package_desc")
    await callback.answer()

@router.callback_query(F.data == "admin_panel")
async def back_to_admin_panel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🔧 Админ-панель\n"
        "Выберите действие:",
        reply_markup=get_admin_menu()
    )
    await callback.answer()

# === УДАЛЕНИЕ ===

@router.callback_query(F.data == "admin_delete")
async def start_delete(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = [
        [InlineKeyboardButton(text="🗑 Удалить категорию", callback_data="delete_category")],
        [InlineKeyboardButton(text="🗑 Удалить пакет", callback_data="delete_package")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
    ]

    await callback.message.edit_text(
        "Что хотите удалить?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

# === УДАЛЕНИЕ КАТЕГОРИИ ===

@router.callback_query(F.data == "delete_category")
async def choose_category_to_delete(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    all_categories = await db.get_all_categories_with_subcategories()

    if not all_categories:
        await callback.message.answer("❌ Нет категорий для удаления!")
        await callback.answer()
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = []

    for cat_id, name, emoji, level in all_categories:
        prefix = "  " * level
        keyboard.append([InlineKeyboardButton(
            text=f"{prefix}{emoji} {name}",
            callback_data=f"delcat_{cat_id}"
        )])

    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")])

    await callback.message.edit_text(
        "⚠️ Выберите категорию для удаления:\n"
        "(При удалении категории будут удалены все подкатегории и пакеты внутри)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(DeleteStates.choosing_category)
    await callback.answer()

@router.callback_query(DeleteStates.choosing_category, F.data.startswith("delcat_"))
async def confirm_category_deletion(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[1])
    await state.update_data(category_id=category_id)

    cat_info = await db.get_category_info(category_id)

    # Подсчитываем что будет удалено
    has_subcats = await db.has_subcategories(category_id)
    has_packages = await db.has_packages(category_id)

    warning = f"⚠️ Вы собираетесь удалить категорию:\n{cat_info['emoji']} {cat_info['name']}\n\n"
    if has_subcats or has_packages:
        warning += "ВНИМАНИЕ: Будут также удалены:\n"
        if has_subcats:
            warning += "- Все подкатегории\n"
        if has_packages:
            warning += "- Все пакеты и их документы\n"

    warning += "\nЭто действие необратимо!"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = [
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete_category")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
    ]

    await callback.message.edit_text(
        warning,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(DeleteStates.confirming_deletion)
    await callback.answer()

@router.callback_query(DeleteStates.confirming_deletion, F.data == "confirm_delete_category")
async def execute_category_deletion(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    category_id = data['category_id']

    cat_info = await db.get_category_info(category_id)

    try:
        await db.delete_category(category_id)
        await callback.message.edit_text(
            f"✅ Категория '{cat_info['emoji']} {cat_info['name']}' успешно удалена!"
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка при удалении: {str(e)}")

    await state.clear()
    await callback.answer()

# === УДАЛЕНИЕ ПАКЕТА ===

@router.callback_query(F.data == "delete_package")
async def choose_package_to_delete(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    all_packages = await db.get_all_packages()

    if not all_packages:
        await callback.message.answer("❌ Нет пакетов для удаления!")
        await callback.answer()
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = []

    for pack_id, pack_name, cat_name, cat_emoji in all_packages:
        keyboard.append([InlineKeyboardButton(
            text=f"📦 {pack_name} (в {cat_emoji} {cat_name})",
            callback_data=f"delpack_{pack_id}"
        )])

    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")])

    await callback.message.edit_text(
        "⚠️ Выберите пакет для удаления:\n"
        "(При удалении пакета будут удалены все его документы)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(DeleteStates.choosing_package)
    await callback.answer()

@router.callback_query(DeleteStates.choosing_package, F.data.startswith("delpack_"))
async def confirm_package_deletion(callback: CallbackQuery, state: FSMContext):
    package_id = int(callback.data.split("_")[1])
    await state.update_data(package_id=package_id)

    pack_info = await db.get_package_info(package_id)
    documents = await db.get_package_documents(package_id)

    warning = f"⚠️ Вы собираетесь удалить пакет:\n📦 {pack_info['name']}\n\n"
    warning += f"В пакете {len(documents)} документов\n"
    warning += "\nЭто действие необратимо!"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = [
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete_package")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
    ]

    await callback.message.edit_text(
        warning,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(DeleteStates.confirming_deletion)
    await callback.answer()

@router.callback_query(DeleteStates.confirming_deletion, F.data == "confirm_delete_package")
async def execute_package_deletion(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    package_id = data['package_id']

    pack_info = await db.get_package_info(package_id)

    try:
        await db.delete_package(package_id)
        await callback.message.edit_text(
            f"✅ Пакет '📦 {pack_info['name']}' успешно удален!"
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка при удалении: {str(e)}")

    await state.clear()
    await callback.answer()

# === УПРАВЛЕНИЕ ДОКУМЕНТАМИ ===

class ManageDocsStates(StatesGroup):
    choosing_action = State()
    choosing_package = State()
    choosing_document = State()
    uploading_new_file = State()
    uploading_additional_files = State()

@router.callback_query(F.data == "admin_manage_docs")
async def start_manage_docs(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = [
        [InlineKeyboardButton(text="🔄 Заменить документ", callback_data="managedoc_replace")],
        [InlineKeyboardButton(text="➕ Добавить документы в пакет", callback_data="managedoc_add")],
        [InlineKeyboardButton(text="🗑 Удалить документ", callback_data="managedoc_delete")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
    ]

    await callback.message.edit_text(
        "📎 Управление документами\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

# === ЗАМЕНА ДОКУМЕНТА ===

@router.callback_query(F.data == "managedoc_replace")
async def choose_package_for_replace(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    all_packages = await db.get_all_packages()

    if not all_packages:
        await callback.message.answer("❌ Нет пакетов!")
        await callback.answer()
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = []

    for pack_id, pack_name, cat_name, cat_emoji in all_packages:
        keyboard.append([InlineKeyboardButton(
            text=f"📦 {pack_name} (в {cat_emoji} {cat_name})",
            callback_data=f"replacepack_{pack_id}"
        )])

    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")])

    await callback.message.edit_text(
        "Выберите пакет:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ManageDocsStates.choosing_package)
    await state.update_data(action="replace")
    await callback.answer()

@router.callback_query(ManageDocsStates.choosing_package, F.data.startswith("replacepack_"))
async def choose_document_to_replace(callback: CallbackQuery, state: FSMContext):
    package_id = int(callback.data.split("_")[1])
    await state.update_data(package_id=package_id)

    documents = await db.get_package_documents(package_id)

    if not documents:
        await callback.message.answer("❌ В этом пакете нет документов!")
        await callback.answer()
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = []

    for doc in documents:
        keyboard.append([InlineKeyboardButton(
            text=f"📄 {doc['filename']}",
            callback_data=f"replacedoc_{doc['id']}"
        )])

    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")])

    await callback.message.edit_text(
        "Выберите документ для замены:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ManageDocsStates.choosing_document)
    await callback.answer()

@router.callback_query(ManageDocsStates.choosing_document, F.data.startswith("replacedoc_"))
async def request_new_file(callback: CallbackQuery, state: FSMContext):
    doc_id = int(callback.data.split("_")[1])
    await state.update_data(doc_id=doc_id)

    doc_info = await db.get_document_info(doc_id)

    await callback.message.answer(
        f"📎 Отправьте новый файл для замены:\n"
        f"Текущий файл: {doc_info['filename']}"
    )
    await state.set_state(ManageDocsStates.uploading_new_file)
    await callback.answer()

@router.message(ManageDocsStates.uploading_new_file, F.document)
async def process_replacement_file(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    doc_id = data['doc_id']

    file_id = message.document.file_id
    file_name = message.document.file_name
    file_size = message.document.file_size

    if file_size > 50 * 1024 * 1024:
        await message.answer("❌ Файл слишком большой (максимум 50 MB)")
        return

    # Удаляем старый файл
    old_doc_info = await db.get_document_info(doc_id)
    if old_doc_info and old_doc_info['file_path']:
        try:
            os.remove(old_doc_info['file_path'])
        except:
            pass

    # Скачиваем новый файл
    file = await bot.get_file(file_id)
    file_path = f"{DOCUMENTS_PATH}/{file_id}_{file_name}"

    os.makedirs(DOCUMENTS_PATH, exist_ok=True)
    await bot.download_file(file.file_path, file_path)

    # Обновляем в базе
    async with aiosqlite.connect(DATABASE_PATH) as db_conn:
        await db_conn.execute(
            "UPDATE Documents SET filename = ?, file_path = ?, file_type = ?, file_id = ?, file_size = ? WHERE id = ?",
            (file_name, file_path, file_name.split('.')[-1] if '.' in file_name else '', file_id, file_size, doc_id)
        )
        await db_conn.commit()

    await message.answer(
        f"✅ Документ успешно заменен!\n"
        f"Новый файл: {file_name}"
    )
    await state.clear()

# === ДОБАВЛЕНИЕ ДОКУМЕНТОВ В ПАКЕТ ===

@router.callback_query(F.data == "managedoc_add")
async def choose_package_for_add(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    all_packages = await db.get_all_packages()

    if not all_packages:
        await callback.message.answer("❌ Нет пакетов!")
        await callback.answer()
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = []

    for pack_id, pack_name, cat_name, cat_emoji in all_packages:
        keyboard.append([InlineKeyboardButton(
            text=f"📦 {pack_name} (в {cat_emoji} {cat_name})",
            callback_data=f"addtopack_{pack_id}"
        )])

    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")])

    await callback.message.edit_text(
        "Выберите пакет для добавления документов:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ManageDocsStates.choosing_package)
    await state.update_data(action="add")
    await callback.answer()

@router.callback_query(ManageDocsStates.choosing_package, F.data.startswith("addtopack_"))
async def request_additional_files(callback: CallbackQuery, state: FSMContext):
    package_id = int(callback.data.split("_")[1])
    await state.update_data(package_id=package_id, files=[])

    pack_info = await db.get_package_info(package_id)

    await callback.message.answer(
        f"📎 Отправьте документы для добавления в пакет:\n"
        f"📦 {pack_info['name']}\n\n"
        f"Можно отправить несколько файлов.\n"
        f"Когда закончите, напишите /done"
    )
    await state.set_state(ManageDocsStates.uploading_additional_files)
    await callback.answer()

@router.message(ManageDocsStates.uploading_additional_files, F.document)
async def process_additional_files(message: Message, state: FSMContext, bot: Bot):
    file_id = message.document.file_id
    file_name = message.document.file_name
    file_size = message.document.file_size

    if file_size > 50 * 1024 * 1024:
        await message.answer("❌ Файл слишком большой (максимум 50 MB)")
        return

    # Скачиваем файл
    file = await bot.get_file(file_id)
    file_path = f"{DOCUMENTS_PATH}/{file_id}_{file_name}"

    os.makedirs(DOCUMENTS_PATH, exist_ok=True)
    await bot.download_file(file.file_path, file_path)

    # Добавляем в список
    data = await state.get_data()
    files = data.get('files', [])
    files.append({
        'file_id': file_id,
        'filename': file_name,
        'file_path': file_path,
        'file_size': file_size,
        'file_type': file_name.split('.')[-1] if '.' in file_name else ''
    })
    await state.update_data(files=files)

    await message.answer(
        f"✅ Файл '{file_name}' сохранен.\n"
        f"Всего файлов: {len(files)}\n\n"
        f"Отправьте еще или напишите /done"
    )

@router.message(ManageDocsStates.uploading_additional_files, Command("done"))
async def finish_adding_documents(message: Message, state: FSMContext):
    data = await state.get_data()
    files = data.get('files', [])
    package_id = data['package_id']

    if not files:
        await message.answer("❌ Вы не загрузили ни одного файла!")
        return

    # Добавляем документы
    for file_info in files:
        await db.create_document(
            package_id=package_id,
            filename=file_info['filename'],
            file_path=file_info['file_path'],
            file_type=file_info['file_type'],
            file_id=file_info['file_id'],
            file_size=file_info['file_size']
        )

    pack_info = await db.get_package_info(package_id)

    await message.answer(
        f"✅ Добавлено {len(files)} документов в пакет '{pack_info['name']}'!"
    )

    await state.clear()

# === УДАЛЕНИЕ ДОКУМЕНТА ===

@router.callback_query(F.data == "managedoc_delete")
async def choose_package_for_delete_doc(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    all_packages = await db.get_all_packages()

    if not all_packages:
        await callback.message.answer("❌ Нет пакетов!")
        await callback.answer()
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = []

    for pack_id, pack_name, cat_name, cat_emoji in all_packages:
        keyboard.append([InlineKeyboardButton(
            text=f"📦 {pack_name} (в {cat_emoji} {cat_name})",
            callback_data=f"delpackdoc_{pack_id}"
        )])

    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")])

    await callback.message.edit_text(
        "Выберите пакет:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ManageDocsStates.choosing_package)
    await state.update_data(action="delete")
    await callback.answer()

@router.callback_query(ManageDocsStates.choosing_package, F.data.startswith("delpackdoc_"))
async def choose_document_to_delete(callback: CallbackQuery, state: FSMContext):
    package_id = int(callback.data.split("_")[1])
    await state.update_data(package_id=package_id)

    documents = await db.get_package_documents(package_id)

    if not documents:
        await callback.message.answer("❌ В этом пакете нет документов!")
        await callback.answer()
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = []

    for doc in documents:
        keyboard.append([InlineKeyboardButton(
            text=f"📄 {doc['filename']}",
            callback_data=f"deldoc_{doc['id']}"
        )])

    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")])

    await callback.message.edit_text(
        "⚠️ Выберите документ для удаления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(ManageDocsStates.choosing_document)
    await callback.answer()

@router.callback_query(ManageDocsStates.choosing_document, F.data.startswith("deldoc_"))
async def execute_document_deletion(callback: CallbackQuery, state: FSMContext):
    doc_id = int(callback.data.split("_")[1])

    doc_info = await db.get_document_info(doc_id)

    try:
        # Удаляем файл
        if doc_info and doc_info['file_path']:
            try:
                os.remove(doc_info['file_path'])
            except:
                pass

        # Удаляем из базы
        await db.delete_document(doc_id)

        await callback.message.edit_text(
            f"✅ Документ '{doc_info['filename']}' успешно удален!"
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка при удалении: {str(e)}")

    await state.clear()
    await callback.answer()

# === ОТМЕНА ===

@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer("❌ Действие отменено")