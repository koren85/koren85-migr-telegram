#!/bin/bash

# Скрипт для установки и настройки MCP серверов для отладки migr-telegram

set -e

echo "🔧 Настройка MCP серверов для migr-telegram..."
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Проверка наличия npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm не найден. Установите Node.js и npm.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ npm найден${NC}"

# Проверка наличия npx
if ! command -v npx &> /dev/null; then
    echo -e "${RED}❌ npx не найден. Установите Node.js и npm.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ npx найден${NC}"

# Проверка наличия sqlite3
if ! command -v sqlite3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  sqlite3 не найден. Рекомендуется установить для проверки БД.${NC}"
else
    echo -e "${GREEN}✅ sqlite3 найден${NC}"
fi

echo ""
echo "📦 Установка MCP серверов..."
echo ""

# Установка SQLite MCP Server
echo "1️⃣ Проверка @modelcontextprotocol/server-sqlite..."
if npx -y @modelcontextprotocol/server-sqlite --help &> /dev/null; then
    echo -e "${GREEN}✅ SQLite MCP server доступен${NC}"
else
    echo -e "${YELLOW}⚠️  SQLite MCP server недоступен, будет установлен при первом использовании${NC}"
fi

# Установка Filesystem MCP Server
echo "2️⃣ Проверка @modelcontextprotocol/server-filesystem..."
if npx -y @modelcontextprotocol/server-filesystem --help &> /dev/null; then
    echo -e "${GREEN}✅ Filesystem MCP server доступен${NC}"
else
    echo -e "${YELLOW}⚠️  Filesystem MCP server недоступен, будет установлен при первом использовании${NC}"
fi

# Установка PostgreSQL MCP Server
echo "3️⃣ Проверка @modelcontextprotocol/server-postgres..."
if npx -y @modelcontextprotocol/server-postgres --help &> /dev/null; then
    echo -e "${GREEN}✅ PostgreSQL MCP server доступен${NC}"
else
    echo -e "${YELLOW}⚠️  PostgreSQL MCP server недоступен, будет установлен при первом использовании${NC}"
fi

echo ""
echo "📝 Настройка конфигурации Claude Desktop..."
echo ""

# Проверка существования директории Claude
CLAUDE_DIR="$HOME/Library/Application Support/Claude"
if [ ! -d "$CLAUDE_DIR" ]; then
    echo -e "${RED}❌ Директория Claude не найдена: $CLAUDE_DIR${NC}"
    echo "Убедитесь, что Claude Desktop установлен."
    exit 1
fi

echo -e "${GREEN}✅ Директория Claude найдена${NC}"

# Создание резервной копии текущей конфигурации
CONFIG_FILE="$CLAUDE_DIR/claude_desktop_config.json"
if [ -f "$CONFIG_FILE" ]; then
    BACKUP_FILE="$CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$CONFIG_FILE" "$BACKUP_FILE"
    echo -e "${GREEN}✅ Создана резервная копия: $BACKUP_FILE${NC}"
fi

# Копирование новой конфигурации
NEW_CONFIG_FILE=".agent/claude_desktop_config.json"
if [ ! -f "$NEW_CONFIG_FILE" ]; then
    echo -e "${RED}❌ Файл конфигурации не найден: $NEW_CONFIG_FILE${NC}"
    exit 1
fi

cp "$NEW_CONFIG_FILE" "$CONFIG_FILE"
echo -e "${GREEN}✅ Конфигурация применена${NC}"

echo ""
echo "🔍 Проверка базы данных SQLite..."
echo ""

# Проверка существования БД
DB_FILE="data/notifications.db"
if [ ! -f "$DB_FILE" ]; then
    echo -e "${YELLOW}⚠️  База данных не найдена: $DB_FILE${NC}"
    echo "Запустите приложение для создания базы данных."
else
    echo -e "${GREEN}✅ База данных найдена: $DB_FILE${NC}"
    
    # Вывод таблиц
    if command -v sqlite3 &> /dev/null; then
        echo ""
        echo "Таблицы в базе данных:"
        sqlite3 "$DB_FILE" ".tables"
        
        echo ""
        echo "Количество записей:"
        echo -n "  - Правила уведомлений: "
        sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM notification_rules;"
        echo -n "  - История уведомлений: "
        sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM notification_history;"
        echo -n "  - Мониторы: "
        sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM monitors;"
    fi
fi

echo ""
echo -e "${GREEN}✅ Настройка завершена!${NC}"
echo ""
echo "📋 Следующие шаги:"
echo "  1. Перезапустите Claude Desktop для применения изменений"
echo "  2. Проверьте доступность MCP серверов в интерфейсе Claude"
echo "  3. Начните отладку приложения!"
echo ""
echo "📚 Документация: .agent/MCP_SETUP.md"
echo ""
