from os import getenv
from dotenv import load_dotenv

load_dotenv()

# Токен бота
BOT_TOKEN = getenv("BOT_TOKEN")

# ID администраторов
ADMIN_IDS = [int(id.strip()) for id in getenv("ADMIN_IDS", "").split(",") if id.strip()]

# Настройки файлов
MAX_FILE_SIZE = int(getenv("MAX_FILE_SIZE", 52428800))
ALLOWED_FILE_TYPES = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'png', 'jpg', 'jpeg']

# Пути
DATABASE_PATH = "bot.db"
DOCUMENTS_PATH = "documents"
TEMP_PATH = "temp"