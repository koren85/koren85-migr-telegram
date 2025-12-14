#!/bin/bash
set -e

echo "🐳 Запуск Database Monitor Telegram Bot в Docker..."

# Проверяем обязательные переменные окружения
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ ОШИБКА: Не установлена переменная TELEGRAM_BOT_TOKEN"
    exit 1
fi

if [ -z "$TELEGRAM_ADMIN_USER_ID" ]; then
    echo "⚠️  ПРЕДУПРЕЖДЕНИЕ: Не установлена переменная TELEGRAM_ADMIN_USER_ID"
fi

# Проверяем наличие JDBC драйвера
if [ ! -f "/app/lib/postgresql.jar" ]; then
    echo "❌ ОШИБКА: Не найден JDBC драйвер PostgreSQL в /app/lib/postgresql.jar"
    echo "📁 Содержимое /app/lib/:"
    ls -la /app/lib/ || echo "Директория /app/lib/ не существует"
    exit 1
fi

# Проверяем наличие конфигурационного файла
if [ ! -f "/app/config.yaml" ]; then
    echo "❌ ОШИБКА: Не найден файл конфигурации /app/config.yaml"
    exit 1
fi

# Создаем необходимые директории
mkdir -p /app/logs /app/data

# Проверяем соединение с базой данных (опционально)
echo "🔍 Проверка переменных окружения..."
echo "TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:0:10}..." 
echo "TELEGRAM_ADMIN_USER_ID: $TELEGRAM_ADMIN_USER_ID"
echo "DATABASE_URL: $DATABASE_URL"
echo "DATABASE_USER: $DATABASE_USER"
echo "LOG_LEVEL: $LOG_LEVEL"

# Показываем информацию о Java
echo "☕ Java версия:"
java -version

echo "🚀 Запуск приложения..."

# Запускаем основное приложение
exec python main.py