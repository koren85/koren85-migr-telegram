# 🔧 Настройка MCP Серверов для Отладки migr-telegram

## 📋 Обзор

Этот документ описывает настройку MCP (Model Context Protocol) серверов для эффективной отладки приложения **migr-telegram** - системы мониторинга баз данных с уведомлениями в Telegram.

## 🎯 Анализ приложения

### Архитектура приложения:
- **Backend**: Python (FastAPI + asyncio)
- **Frontend**: Vue.js 3 + Bootstrap 5
- **База данных**: SQLite (`data/notifications.db`)
- **Конфигурация**: YAML (`config.yaml`)
- **Внешние БД**: PostgreSQL через JDBC
- **Уведомления**: Telegram Bot API

### Ключевые компоненты:
1. **Database Monitors** - мониторинг PostgreSQL баз данных
2. **Notification Rules Engine** - обработка правил уведомлений
3. **Web Server** (FastAPI) - REST API и веб-интерфейс
4. **Telegram Bot** - бот для уведомлений и команд
5. **SQLite Database** - хранение правил, истории, мониторов

## 🚀 Рекомендуемые MCP Серверы

### 1. **SQLite MCP Server** ⭐ ОБЯЗАТЕЛЬНО

**Зачем нужен:**
- Доступ к базе данных уведомлений (`data/notifications.db`)
- Проверка созданных правил (таблица `notification_rules`)
- Анализ истории уведомлений (таблица `notification_history`)
- Просмотр конфигураций мониторов (таблица `monitors`)
- Отладка состояний мониторов (таблица `disabled_monitors`)

**Таблицы в БД:**
- `notification_rules` - правила уведомлений
- `notification_history` - история отправленных уведомлений
- `disabled_monitors` - отключенные мониторы
- `monitors` - конфигурации мониторов
- `migration_history` - история миграций из config.yaml

**Установка:**
```bash
npm install -g @modelcontextprotocol/server-sqlite
```

**Конфигурация для Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "sqlite": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sqlite",
        "/Users/aleksandrcernaev/projects/migr-telegram/data/notifications.db"
      ]
    }
  }
}
```

**Примеры использования:**
```sql
-- Посмотреть все активные правила
SELECT * FROM notification_rules WHERE is_active = 1;

-- Проверить историю уведомлений за последние 24 часа
SELECT * FROM notification_history 
WHERE sent_at > datetime('now', '-24 hours')
ORDER BY sent_at DESC;

-- Посмотреть все мониторы
SELECT * FROM monitors WHERE is_active = 1;

-- Проверить отключенные мониторы
SELECT * FROM disabled_monitors;
```

### 2. **Filesystem MCP Server** ⭐ ОБЯЗАТЕЛЬНО

**Зачем нужен:**
- Чтение и анализ конфигурационных файлов (`config.yaml`)
- Просмотр логов приложения (`logs/app.log`)
- Доступ к исходному коду для анализа ошибок
- Чтение документации проекта

**Установка:**
```bash
npm install -g @modelcontextprotocol/server-filesystem
```

**Конфигурация для Claude Desktop:**
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/aleksandrcernaev/projects/migr-telegram"
      ]
    }
  }
}
```

**Важные файлы для мониторинга:**
- `config.yaml` - конфигурация баз данных и мониторов
- `logs/app.log` - логи приложения
- `web/server.py` - FastAPI сервер
- `notifications/database.py` - работа с SQLite
- `notifications/rules_engine.py` - движок правил
- `static/app.js` - Frontend код

### 3. **PostgreSQL MCP Server** ⭐ РЕКОМЕНДУЕТСЯ

**Зачем нужен:**
- Прямой доступ к мониторируемым PostgreSQL базам данных
- Отладка SQL запросов мониторов
- Проверка данных в реальных БД
- Тестирование подключений и запросов

**Установка:**
```bash
npm install -g @modelcontextprotocol/server-postgres
```

**Конфигурация для Claude Desktop** (пример для одной БД):
```json
{
  "mcpServers": {
    "postgres-irk": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://tomcat:G18sBB07uK@10.209.109.137:5436/migration"
      ]
    }
  }
}
```

**⚠️ Примечание:** Из соображений безопасности, можно настроить только для тестовой БД или использовать read-only пользователя.

### 4. **GitHub MCP Server** 📦 ОПЦИОНАЛЬНО

**Зачем нужен:**
- Если проект находится на GitHub
- Для проверки Issues, Pull Requests
- Анализ истории коммитов
- Работа с GitHub Actions

**Установка:**
```bash
npm install -g @modelcontextprotocol/server-github
```

**Конфигурация:**
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your_github_token_here"
      }
    }
  }
}
```

### 5. **Memory MCP Server** 📝 ОПЦИОНАЛЬНО

**Зачем нужен:**
- Сохранение контекста между сессиями отладки
- Запоминание найденных проблем и решений
- Ведение заметок о конфигурации

**Установка:**
```bash
npm install -g @modelcontextprotocol/server-memory
```

**Конфигурация:**
```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    }
  }
}
```

## 📝 Полная Конфигурация Claude Desktop

Скомбинированная конфигурация всех рекомендуемых MCP серверов:

**Файл:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "sqlite": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sqlite",
        "/Users/aleksandrcernaev/projects/migr-telegram/data/notifications.db"
      ]
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/aleksandrcernaev/projects/migr-telegram"
      ]
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    }
  }
}
```

## 🔍 Сценарии Отладки с MCP

### Сценарий 1: Проблема с правилами уведомлений

**Проблема:** Правило не срабатывает  
**MCP серверы:** SQLite + Filesystem

**Шаги отладки:**
1. **SQLite**: Проверить правило в `notification_rules`
2. **SQLite**: Проверить историю в `notification_history`
3. **Filesystem**: Посмотреть логи в `logs/app.log`
4. **Filesystem**: Проверить код в `notifications/rules_engine.py`

### Сценарий 2: Проблема с мониторами БД

**Проблема:** Монитор не обновляется  
**MCP серверы:** SQLite + PostgreSQL + Filesystem

**Шаги отладки:**
1. **SQLite**: Проверить конфигурацию в таблице `monitors`
2. **PostgreSQL**: Протестировать SQL запрос монитора напрямую
3. **Filesystem**: Посмотреть `config.yaml` и логи
4. **Filesystem**: Проверить код подключения в `database/connection.py`

### Сценарий 3: Отладка веб-интерфейса

**Проблема:** Данные не отображаются в UI  
**MCP серверы:** SQLite + Filesystem

**Шаги отладки:**
1. **SQLite**: Проверить данные в базе
2. **Filesystem**: Проверить API endpoints в `web/server.py`
3. **Filesystem**: Проверить Frontend код в `static/app.js`
4. **Filesystem**: Посмотреть логи сервера

## 🛠️ Команды для Проверки MCP Серверов

После настройки MCP серверов, проверьте их работу:

### Проверка SQLite MCP:
```bash
# Подключение к базе данных напрямую (для проверки)
sqlite3 /Users/aleksandrcernaev/projects/migr-telegram/data/notifications.db ".tables"
```

### Проверка Filesystem MCP:
```bash
# Проверка прав доступа
ls -la /Users/aleksandrcernaev/projects/migr-telegram/
```

### Проверка конфигурации Claude Desktop:
```bash
# Просмотр конфигурации
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | jq
```

## 📊 Структура Базы Данных SQLite

### notification_rules
```sql
CREATE TABLE notification_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    monitor_name TEXT NOT NULL,
    db_name TEXT NOT NULL,
    condition_type TEXT NOT NULL,
    condition_value TEXT,
    condition_duration INTEGER,
    cooldown_seconds INTEGER NOT NULL DEFAULT 300,
    priority TEXT NOT NULL DEFAULT 'medium',
    message_template TEXT NOT NULL,
    target_chats TEXT NOT NULL DEFAULT 'all',
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### notification_history
```sql
CREATE TABLE notification_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER,
    monitor_name TEXT NOT NULL,
    db_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    message TEXT NOT NULL,
    target_chats TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN NOT NULL DEFAULT 1,
    error_message TEXT,
    FOREIGN KEY (rule_id) REFERENCES notification_rules (id)
);
```

### monitors
```sql
CREATE TABLE monitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    db_name TEXT NOT NULL,
    sql_query TEXT NOT NULL,
    check_interval INTEGER NOT NULL DEFAULT 60,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    driver TEXT,
    url TEXT,
    username TEXT,
    password TEXT,
    jar_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, db_name)
);
```

## 🎯 Приоритетность Настройки

### Обязательно:
1. ✅ **SQLite MCP** - основная база данных приложения
2. ✅ **Filesystem MCP** - доступ к коду и конфигурации

### Рекомендуется:
3. 📦 **PostgreSQL MCP** - для отладки запросов мониторов
4. 📝 **Memory MCP** - для сохранения контекста отладки

### Опционально:
5. 🔧 **GitHub MCP** - если проект на GitHub

## 📖 Дополнительные Ресурсы

- [MCP Specification](https://modelcontextprotocol.io/)
- [MCP Servers Repository](https://github.com/modelcontextprotocol/servers)
- [Claude Desktop Configuration](https://docs.anthropic.com/claude/docs/mcp)

## 🔒 Безопасность

**Важные замечания:**
- ⚠️ Не храните пароли в открытом виде в конфигурации MCP
- 🔐 Используйте переменные окружения для конфиденциальных данных
- 🛡️ Для production БД создайте read-only пользователя
- 📝 Храните токены и пароли в отдельных `.env` файлах

## 🎓 Следующие Шаги

После настройки MCP серверов:

1. **Перезапустите Claude Desktop** для применения конфигурации
2. **Проверьте доступность** серверов через интерфейс Claude
3. **Протестируйте запросы** к базе данных
4. **Начните отладку** вашего приложения

---

**Автор:** MCP Setup Guide for migr-telegram  
**Дата:** 2026-01-25  
**Версия:** 1.0
