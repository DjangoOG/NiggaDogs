#!/bin/bash

# Скрипт для первоначальной настройки на сервере

set -e

BOT_DIR="/opt/telegram-bot"
SERVICE_NAME="telegram-bot"

echo "🚀 Начинаем развертывание Telegram бота..."

# Создаем директорию для бота
sudo mkdir -p $BOT_DIR
sudo chown $USER:$USER $BOT_DIR

# Клонируем репозиторий (замените на ваш URL)
if [ ! -d "$BOT_DIR/.git" ]; then
    echo "📦 Клонирование репозитория..."
    git clone <YOUR_REPO_URL> $BOT_DIR
else
    echo "📦 Обновление репозитория..."
    cd $BOT_DIR
    git pull origin main
fi

cd $BOT_DIR

# Создаем виртуальное окружение
if [ ! -d "venv" ]; then
    echo "🐍 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активируем и устанавливаем зависимости
echo "📚 Установка зависимостей..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Создаем .env файл если его нет
if [ ! -f ".env" ]; then
    echo "⚙️ Создание .env файла..."
    cp .env.example .env
    echo "⚠️ ВАЖНО: Отредактируйте файл $BOT_DIR/.env и укажите ваши данные!"
    echo "   После этого выполните: sudo systemctl start $SERVICE_NAME"
    read -p "Нажмите Enter после редактирования .env..."
fi

# Инициализация БД
echo "🗄️ Инициализация базы данных..."
python init_db.py

# Создаем директорию для документов
mkdir -p documents

# Создаем systemd service
echo "⚙️ Создание systemd сервиса..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=Telegram Document Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOT_DIR
Environment="PATH=$BOT_DIR/venv/bin"
ExecStart=$BOT_DIR/venv/bin/python $BOT_DIR/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Перезагружаем systemd и запускаем сервис
echo "🔄 Запуск сервиса..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

echo ""
echo "✅ Развертывание завершено!"
echo ""
echo "📋 Полезные команды:"
echo "   Проверить статус: sudo systemctl status $SERVICE_NAME"
echo "   Посмотреть логи: sudo journalctl -u $SERVICE_NAME -f"
echo "   Перезапустить: sudo systemctl restart $SERVICE_NAME"
echo "   Остановить: sudo systemctl stop $SERVICE_NAME"
echo ""
echo "⚠️ Не забудьте настроить .env файл: nano $BOT_DIR/.env"
