from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram import Bot

from keyboards.user_kb import get_main_menu, get_category_content, get_package_keyboard
from database import Database

router = Router()
db = Database()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Добро пожаловать в базу шаблонов документов!\n"
        "Выберите нужную категорию:",
        reply_markup=await get_main_menu()
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📚 Справка по боту:\n\n"
        "Используйте кнопки для навигации по базе документов.\n"
        "📁 - категории/подкатегории\n"
        "📦 - пакеты с документами\n"
        "📄 - отдельные документы\n\n"
        "Команды:\n"
        "/start - главное меню\n"
        "/help - эта справка"
    )

@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "👋 Главное меню\n"
        "Выберите категорию:",
        reply_markup=await get_main_menu()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("cat_"))
async def show_category(callback: CallbackQuery):
    category_id = int(callback.data.split("_")[1])
    
    # Получаем информацию о категории
    category_info = await db.get_category_info(category_id)
    if not category_info:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return
    
    category_name = f"{category_info['emoji']} {category_info['name']}"
    
    # Формируем текст сообщения
    text = f"{category_name}\n"
    if category_info['description']:
        text += f"\n{category_info['description']}\n"
    
    # Проверяем есть ли подкатегории или пакеты
    has_subcats = await db.has_subcategories(category_id)
    has_packages = await db.has_packages(category_id)
    
    if has_subcats and has_packages:
        text += "\nВыберите подкатегорию или пакет:"
    elif has_subcats:
        text += "\nВыберите подкатегорию:"
    elif has_packages:
        text += "\nВыберите пакет:"
    else:
        text += "\n⚠️ В этой категории пока нет содержимого"
    
    await callback.message.edit_text(
        text,
        reply_markup=await get_category_content(category_id, category_info['parent_id'])
    )
    await callback.answer()

@router.callback_query(F.data.startswith("pack_"))
async def show_package(callback: CallbackQuery):
    package_id = int(callback.data.split("_")[1])
    
    # Получаем информацию о пакете
    package_info = await db.get_package_info(package_id)
    if not package_info:
        await callback.answer("❌ Пакет не найден", show_alert=True)
        return
    
    text = f"📦 Пакет: {package_info['name']}\n"
    if package_info['description']:
        text += f"\n{package_info['description']}\n"
    
    text += f"\nВыберите документ:"
    
    await callback.message.edit_text(
        text,
        reply_markup=await get_package_keyboard(package_id, package_info['category_id'])
    )
    await callback.answer()

@router.callback_query(F.data.startswith("doc_"))
async def send_document(callback: CallbackQuery, bot: Bot):
    doc_id = int(callback.data.split("_")[1])
    doc_info = await db.get_document_info(doc_id)
    
    if not doc_info:
        await callback.answer("❌ Документ не найден", show_alert=True)
        return
    
    # Сначала показываем статус
    status_msg = await callback.message.answer("📎 Отправляю документ...")
    
    try:
        # Если есть сохраненный file_id - используем его
        if doc_info['file_id']:
            await bot.send_document(
                callback.from_user.id,
                doc_info['file_id'],
                caption=f"📄 {doc_info['filename']}"
            )
        else:
            # Иначе отправляем файл и сохраняем file_id
            with open(doc_info['file_path'], 'rb') as file:
                sent_msg = await bot.send_document(
                    callback.from_user.id,
                    file,
                    caption=f"📄 {doc_info['filename']}"
                )
                
                # Сохраняем file_id
                file_id = sent_msg.document.file_id
                await db.update_document_file_id(doc_id, file_id)
        
        await status_msg.delete()
        await callback.answer("✅ Документ отправлен!")
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка при отправке: {str(e)}")
        await callback.answer("Ошибка отправки", show_alert=True)