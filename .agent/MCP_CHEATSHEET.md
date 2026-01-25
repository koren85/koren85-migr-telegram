# 🚀 MCP Cheat Sheet - Отладка migr-telegram

## 📊 Доступные MCP Серверы

### 1. **sqlite-migr-telegram**
**База данных:** `/Users/aleksandrcernaev/projects/migr-telegram/data/notifications.db`

#### Полезные запросы:

```sql
-- Посмотреть все активные правила
SELECT id, name, monitor_name, db_name, condition_type, is_active 
FROM notification_rules 
WHERE is_active = 1;

-- Последние 10 уведомлений
SELECT * FROM notification_history 
ORDER BY sent_at DESC LIMIT 10;

-- Статистика по правилам
SELECT 
  db_name, 
  COUNT(*) as total_rules,
  SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_rules
FROM notification_rules
GROUP BY db_name;

-- Проверить мониторы
SELECT id, name, db_name, is_active, check_interval 
FROM monitors 
ORDER BY db_name, name;

-- Найти правило по имени
SELECT * FROM notification_rules 
WHERE name LIKE '%keyword%';

-- История неудачных уведомлений
SELECT * FROM notification_history 
WHERE success = 0 
ORDER BY sent_at DESC LIMIT 20;

-- Отключенные мониторы
SELECT * FROM disabled_monitors;
```

### 2. **filesystem-migr-telegram**
**Путь:** `/Users/aleksandrcernaev/projects/migr-telegram`

#### Важные файлы:

```
📂 Конфигурация:
  - config.yaml - настройки баз данных и мониторов
  - .env - переменные окружения

📂 Код:
  - web/server.py - FastAPI endpoints
  - notifications/database.py - работа с SQLite
  - notifications/rules_engine.py - движок правил
  - static/app.js - Vue.js frontend

📂 Логи:
  - logs/app.log - основные логи приложения

📂 База данных:
  - data/notifications.db - SQLite база
```

### 3. **postgres-irk-migr**
**Подключение:** `postgresql://tomcat:***@10.209.109.137:5436/migration`

#### Тестовые запросы (из config.yaml):

```sql
-- Иркутск 3 задача (файловые задачи)
SELECT a_status FROM BDM_FILE_TASK bdm3 
JOIN cms_task t ON t.ouid=bdm3.ouid LIMIT 1;

-- Иркутск 1 задача (структурные задачи)
SELECT a_status FROM BDM_STRUCTURE_TASK bdm1 
JOIN cms_task t ON t.ouid=bdm1.ouid LIMIT 1;

-- Иркутск 2 задача (базовые задачи)
SELECT a_status FROM BDM_TASK bdm2 
JOIN cms_task t ON t.ouid=bdm2.ouid LIMIT 1;
```

## 🔍 Типичные Сценарии Отладки

### Сценарий 1: Правило не срабатывает

**Шаги отладки:**

1️⃣ Проверьте, что правило активно:
```sql
SELECT * FROM notification_rules WHERE name = 'имя_правила';
```

2️⃣ Проверьте монитор:
```sql
SELECT * FROM monitors WHERE name = 'имя_монитора';
```

3️⃣ Проверьте историю уведомлений:
```sql
SELECT * FROM notification_history 
WHERE monitor_name = 'имя_монитора' 
ORDER BY sent_at DESC LIMIT 10;
```

4️⃣ Посмотрите логи приложения:
```bash
tail -100 logs/app.log | grep "имя_монитора"
```

### Сценарий 2: Монитор не обновляется

**Шаги отладки:**

1️⃣ Проверьте конфигурацию монитора в SQLite:
```sql
SELECT * FROM monitors WHERE name = 'имя_монитора';
```

2️⃣ Проверьте, не отключен ли монитор:
```sql
SELECT * FROM disabled_monitors WHERE monitor_name = 'имя_монитора';
```

3️⃣ Протестируйте SQL запрос напрямую в PostgreSQL:
```sql
-- Используйте postgres-irk-migr MCP
-- Скопируйте sql_query из таблицы monitors и выполните
```

4️⃣ Проверьте логи подключения:
```bash
tail -100 logs/app.log | grep -E "(connection|error|монитор)"
```

### Сценарий 3: Много дублирующихся уведомлений

**Шаги отладки:**

1️⃣ Проверьте cooldown правила:
```sql
SELECT name, monitor_name, cooldown_seconds 
FROM notification_rules 
WHERE name = 'имя_правила';
```

2️⃣ Увеличьте cooldown:
```sql
UPDATE notification_rules 
SET cooldown_seconds = 600 
WHERE id = rule_id;
```

3️⃣ Проверьте частоту уведомлений в истории:
```sql
SELECT 
  monitor_name,
  COUNT(*) as notification_count,
  MIN(sent_at) as first_notification,
  MAX(sent_at) as last_notification
FROM notification_history
WHERE sent_at > datetime('now', '-1 hour')
GROUP BY monitor_name
ORDER BY notification_count DESC;
```

### Сценарий 4: Веб-интерфейс не показывает данные

**Шаги отладки:**

1️⃣ Проверьте данные в SQLite:
```sql
SELECT COUNT(*) FROM notification_rules;
SELECT COUNT(*) FROM monitors;
SELECT COUNT(*) FROM notification_history;
```

2️⃣ Проверьте API endpoints (через браузер или curl):
```bash
curl http://localhost:8090/api/stats
curl http://localhost:8090/api/rules
curl http://localhost:8090/api/monitors
```

3️⃣ Проверьте frontend код:
- Откройте файл: `static/app.js`
- Ищите ошибки в console.log

4️⃣ Проверьте логи сервера:
```bash
tail -100 logs/app.log | grep -E "(GET|POST|ERROR)"
```

## 📖 Полезные SQL Запросы

### Аналитика по уведомлениям

```sql
-- Топ-5 самых активных мониторов (по количеству уведомлений)
SELECT 
  monitor_name, 
  COUNT(*) as notification_count
FROM notification_history
WHERE sent_at > datetime('now', '-7 days')
GROUP BY monitor_name
ORDER BY notification_count DESC
LIMIT 5;

-- Процент успешных уведомлений за последние 24 часа
SELECT 
  ROUND(CAST(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS FLOAT) * 100.0 / COUNT(*), 2) as success_rate
FROM notification_history
WHERE sent_at > datetime('now', '-24 hours');

-- Неактивные правила (которые давно не срабатывали)
SELECT 
  nr.name,
  nr.monitor_name,
  MAX(nh.sent_at) as last_notification
FROM notification_rules nr
LEFT JOIN notification_history nh ON nr.id = nh.rule_id
WHERE nr.is_active = 1
GROUP BY nr.id
HAVING last_notification IS NULL OR last_notification < datetime('now', '-7 days')
ORDER BY last_notification ASC;
```

### Управление правилами

```sql
-- Активировать/деактивировать правило
UPDATE notification_rules SET is_active = 1 WHERE id = rule_id;
UPDATE notification_rules SET is_active = 0 WHERE id = rule_id;

-- Изменить cooldown
UPDATE notification_rules SET cooldown_seconds = 600 WHERE id = rule_id;

-- Найти правила с определенным типом условия
SELECT * FROM notification_rules WHERE condition_type = 'value_changed';

-- Удалить старую историю (старше 30 дней)
DELETE FROM notification_history WHERE sent_at < datetime('now', '-30 days');
```

## 🛠️ Быстрые Команды

### Проверка состояния приложения

```bash
# Проверка процесса
ps aux | grep python | grep main.py

# Проверка порта
lsof -i :8090

# Последние логи
tail -50 logs/app.log

# Логи в реальном времени
tail -f logs/app.log

# Поиск ошибок в логах
grep -i error logs/app.log | tail -20
```

### Работа с базой данных

```bash
# Открыть SQLite в интерактивном режиме
sqlite3 data/notifications.db

# Экспорт данных
sqlite3 data/notifications.db ".dump" > backup.sql

# Проверка размера БД
du -h data/notifications.db

# Вакуум БД (оптимизация)
sqlite3 data/notifications.db "VACUUM;"
```

## 🔄 Перезапуск служб

```bash
# Остановить приложение
pkill -f "python main.py"

# Запустить приложение
python main.py &

# Запустить с debug логами
python main.py --debug &

# Проверить статус
curl http://localhost:8090/api/stats
```

## 📚 Дополнительные Ресурсы

- **Документация MCP**: `.agent/MCP_SETUP.md`
- **README проекта**: `README.md`
- **Конфигурация**: `config.yaml`
- **API документация**: http://localhost:8090/docs (когда сервер запущен)

---

**Обновлено:** 2026-01-25  
**Версия:** 1.0
