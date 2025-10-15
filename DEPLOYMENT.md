# Инструкция по развертыванию

## Шаг 1: Настройка GitHub репозитория

1. Создайте репозиторий на GitHub
2. Добавьте секреты в Settings → Secrets and variables → Actions:
   - `SERVER_HOST` - IP адрес или домен вашего сервера
   - `SERVER_USER` - имя пользователя для SSH (обычно `root` или ваше имя)
   - `SERVER_SSH_KEY` - приватный SSH ключ для доступа к серверу
   - `SERVER_PORT` - порт SSH (обычно 22)

### Как получить SSH ключ:

На вашем локальном компьютере:
```bash
# Генерация SSH ключа (если у вас его нет)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Копируем публичный ключ на сервер
ssh-copy-id user@your-server-ip

# Копируем приватный ключ для GitHub Secrets
cat ~/.ssh/id_ed25519
# Скопируйте весь вывод и вставьте в SERVER_SSH_KEY
```

## Шаг 2: Первоначальная настройка сервера

### Подключитесь к серверу:
```bash
ssh user@your-server-ip
```

### Установите необходимые пакеты:
```bash
# Для Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

# Для CentOS/RHEL
sudo yum install -y python3 python3-pip git
```

### Скачайте и выполните скрипт развертывания:
```bash
# Скачайте deploy.sh из репозитория
wget https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/deploy.sh

# Отредактируйте скрипт и укажите URL вашего репозитория
nano deploy.sh
# Найдите строку <YOUR_REPO_URL> и замените на
# https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Сделайте скрипт исполняемым
chmod +x deploy.sh

# Запустите скрипт
./deploy.sh
```

### Настройте переменные окружения:
```bash
nano /opt/telegram-bot/.env
```

Укажите ваши данные:
```
BOT_TOKEN=ваш_токен_от_BotFather
ADMIN_IDS=ваш_telegram_id
MAX_FILE_SIZE=52428800
```

### Перезапустите бота:
```bash
sudo systemctl restart telegram-bot
```

## Шаг 3: Проверка работы

Проверьте статус бота:
```bash
sudo systemctl status telegram-bot
```

Просмотр логов в реальном времени:
```bash
sudo journalctl -u telegram-bot -f
```

## Автоматический деплой

После настройки при каждом `git push` в ветку `main`:
1. GitHub Actions автоматически подключится к серверу
2. Скачает последние изменения
3. Обновит зависимости
4. Перезапустит бота

## Полезные команды

```bash
# Проверить статус
sudo systemctl status telegram-bot

# Посмотреть логи
sudo journalctl -u telegram-bot -f

# Перезапустить бота
sudo systemctl restart telegram-bot

# Остановить бота
sudo systemctl stop telegram-bot

# Запустить бота
sudo systemctl start telegram-bot

# Обновить вручную
cd /opt/telegram-bot
git pull
sudo systemctl restart telegram-bot
```

## Решение проблем

### Бот не запускается:
```bash
# Проверьте логи
sudo journalctl -u telegram-bot -n 50

# Проверьте .env файл
cat /opt/telegram-bot/.env

# Проверьте права доступа
ls -la /opt/telegram-bot
```

### GitHub Actions не может подключиться к серверу:
1. Проверьте правильность секретов в GitHub
2. Убедитесь, что SSH ключ добавлен на сервер
3. Проверьте, что порт SSH открыт в firewall

### Проблемы с правами доступа:
```bash
sudo chown -R $USER:$USER /opt/telegram-bot
chmod +x /opt/telegram-bot/deploy.sh
```
