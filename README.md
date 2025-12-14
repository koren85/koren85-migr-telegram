# 🔔 Database Monitoring System с умными уведомлениями

Комплексная система мониторинга баз данных с гибкими правилами уведомлений, веб-интерфейсом управления и поддержкой Telegram групп.

## 🚀 Основные возможности

### 📊 Мониторинг
- **Мониторинг нескольких БД** одновременно через JDBC
- **Произвольные SQL запросы** для каждого монитора
- **Настраиваемые интервалы** проверки
- **Автоматическое переподключение** при сбоях

### 🧠 Умные уведомления
- **8 типов условий** для срабатывания правил
- **4 уровня приоритета** с цветовой индикацией
- **Анти-спам защита** с cooldown периодами
- **Гибкие шаблоны** сообщений
- **Групповые чаты** Telegram

### 🌐 Веб-управление
- **Современный веб-интерфейс** на Vue.js + Bootstrap
- **Реалтайм мониторинг** состояний
- **Визуальный редактор** правил с тестированием
- **История уведомлений** и аналитика
- **REST API** для интеграций

## 📋 Требования

- **Python 3.8+**
- **Java Runtime Environment** (для JDBC)
- **JDBC драйверы** для ваших БД
- **Telegram бот токен**

## 🛠️ Установка

### 1. Подготовка окружения
```bash
# Клонируем репозиторий
git clone <repository_url>
cd migr-telegram

# Создаем виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или .venv\Scripts\activate  # Windows

# Устанавливаем зависимости
pip install -r requirements.txt
```

### 2. Настройка Telegram бота
1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Получите токен бота
3. Добавьте ваш chat ID в конфигурацию

### 3. Настройка конфигурации
```bash
# Скопируйте пример конфигурации
cp config.yaml config_local.yaml

# Отредактируйте настройки
nano config_local.yaml
```

### 4. JDBC драйверы
Скачайте и поместите JDBC драйверы в папку `lib/`:
- PostgreSQL: `postgresql.jar`
- MySQL: `mysql-connector-java.jar`
- Oracle: `ojdbc.jar`

## ⚙️ Конфигурация

### Базовая структура config.yaml
```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN"
  chat_ids:
    - 123456789  # Ваш Telegram chat ID

databases:
  - name: "production_db"
    driver: "org.postgresql.Driver"
    url: "jdbc:postgresql://localhost:5432/mydb"
    username: "user"
    password: "password"
    jar_path: "./lib/postgresql.jar"
    tables:
      # Новый формат с произвольными SQL запросами
      - name: "order_status_monitor"
        sql_query: "SELECT status FROM orders WHERE created_at > NOW() - INTERVAL '1 hour' ORDER BY id DESC LIMIT 1"
        check_interval: 30
      
      # Или legacy формат (простые таблицы)
      - table: "system_health"
        column: "status"
        check_interval: 60

logging:
  level: "INFO"
  file: "logs/app.log"

monitoring:
  startup_delay: 10
  max_retries: 3
  retry_delay: 5
```

## 🚀 Запуск системы

```bash
# Стандартный запуск
python main.py

# С кастомной конфигурацией
python main.py --config config_local.yaml

# С debug логами
python main.py --debug
```

После запуска будут доступны:
- **Telegram бот** - готов к работе
- **Веб-интерфейс** - http://localhost:8090
- **Мониторинг БД** - автоматически начнется через 10 секунд

## 🌐 Веб-интерфейс управления

### Dashboard (Главная)
- **Статистика в реальном времени**
  - Общее количество правил
  - Активные правила
  - Уведомления за 24 часа
  - Процент успешной доставки
- **Последние уведомления** с деталями

### Rules (Правила уведомлений)
**Создание правил с условиями:**

#### Типы условий:
- **`value_changed`** - при любом изменении значения
- **`value_equals`** - при конкретном значении
- **`value_not_equals`** - при НЕ равенстве значению
- **`value_contains`** - если значение содержит текст
- **`value_unchanged`** - если значение не меняется X секунд
- **`value_greater`** - больше числового значения
- **`value_less`** - меньше числового значения
- **`custom`** - пользовательские Python выражения

#### Уровни приоритета:
- 🔵 **Low** - низкий приоритет
- 🟡 **Medium** - средний приоритет  
- 🟠 **High** - высокий приоритет
- 🔴 **Critical** - критический приоритет

#### Шаблоны сообщений:
Поддерживаются переменные:
- `{monitor_name}` - имя монитора
- `{db_name}` - имя базы данных
- `{old_value}` - предыдущее значение
- `{new_value}` - новое значение
- `{timestamp}` - время срабатывания
- `{same_value_duration}` - длительность без изменений

#### Примеры правил:

**1. Критические ошибки:**
```yaml
Название: Critical Database Error
Условие: value_contains
Значение: error
Cooldown: 300 секунд
Шаблон: 🚨 КРИТИЧНО: {monitor_name} = {new_value}
```

**2. Долгое отсутствие активности:**
```yaml
Название: Service Stuck Alert
Условие: value_unchanged
Длительность: 3600 секунд
Cooldown: 1800 секунд
Шаблон: ⚠️ {monitor_name} не изменяется уже {same_value_duration}
```

**3. Превышение лимитов:**
```yaml
Название: High Load Warning
Условие: value_greater
Значение: 80
Шаблон: 📈 Высокая нагрузка {monitor_name}: {new_value}%
```

**4. Пользовательская логика:**
```yaml
Название: Complex Business Rule
Условие: custom
Значение: int(new_value) > 100 and old_value != new_value
Шаблон: 📊 Превышен бизнес-лимит: {new_value}
```

### Monitors (Состояние мониторов)
Реалтайм просмотр:
- **Текущие значения** всех мониторов
- **История изменений**
- **Время последнего обновления**
- **Активные cooldown'ы**
- **Интервалы проверки**

### History (История)
- **Полная история** всех уведомлений
- **Статус доставки** (успешно/ошибка)
- **Фильтрация** по мониторам и времени
- **Детали ошибок** доставки

## 🤖 Telegram бот команды

### Пользовательские команды:
- **`/start`** - Приветствие и справка
- **`/help`** - Подробная справка по командам
- **`/status`** - Статус всех мониторов БД
- **`/list`** - Список всех мониторов и их настроек
- **`/get <db_name> <monitor_name>`** - Получить текущее значение

### Команды администратора:
- **`/add_group`** - Добавить текущий чат в список уведомлений
- **`/groups`** - Показать все авторизованные чаты

### Примеры использования:
```
/get production_db order_status_monitor
/status
/list
```

## 🔧 Логика работы системы

### 1. **Архитектура мониторинга**

```
┌─ Database Monitors ────────────────────────┐
│  ┌─ PostgreSQL Monitor ─┐                  │
│  │ • SQL запросы        │ ◄────────────────┼─ JDBC Drivers
│  │ • Периодические      │                  │
│  │   проверки (30с)     │                  │
│  └─────────────────────┘                  │
│                                           │
│  ┌─ MySQL Monitor ──────┐                  │
│  │ • Другие запросы     │                  │
│  │ • Свои интервалы     │                  │
│  └─────────────────────┘                  │
└───────────────────────────────────────────┘
                    │
                    ▼
┌─ Notification Rules Engine ───────────────┐
│  ┌─ Условие 1 ─┐ ┌─ Условие 2 ─┐        │
│  │ value_equals│ │ value_stuck │        │
│  │ cooldown    │ │ duration    │        │
│  └─────────────┘ └─────────────┘        │
│                                         │
│  ┌─ Anti-spam ──────────────────────┐   │
│  │ • Cooldown таймеры              │   │
│  │ • Дедупликация                  │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─ Notification Delivery ───────────────────┐
│  ┌─ Telegram API ──────┐ ┌─ Priority ───┐ │
│  │ • Индивидуальные    │ │ 🔴 Critical  │ │
│  │   чаты              │ │ 🟠 High      │ │
│  │ • Групповые чаты    │ │ 🟡 Medium    │ │
│  │ • Retry механизм    │ │ 🔵 Low       │ │
│  └─────────────────────┘ └─────────────┘ │
└───────────────────────────────────────────┘
```

### 2. **Жизненный цикл уведомления**

```
1. [Database Monitor] ──► Выполняет SQL запрос каждые N секунд
                          │
2. [Value Change] ────────► Обнаружено изменение: old_value ≠ new_value
                          │
3. [Rules Engine] ────────► Проверяет все активные правила для этого монитора
                          │
4. [Condition Check] ─────► Для каждого правила проверяет условие:
                          │ • value_equals: new_value == "error"
                          │ • value_unchanged: same_duration > 3600
                          │ • custom: eval("int(new_value) > 100")
                          │
5. [Cooldown Check] ──────► Правило в cooldown? Пропускаем уведомление
                          │
6. [Message Format] ──────► Форматируем сообщение по шаблону:
                          │ "🚨 {monitor_name}: {old_value} → {new_value}"
                          │
7. [Delivery] ────────────► Отправляем в указанные чаты
                          │ • Telegram API
                          │ • Обработка ошибок
                          │ • Логирование результата
                          │
8. [History Log] ─────────► Сохраняем в базу уведомлений:
                          │ • Время отправки
                          │ • Статус доставки
                          │ • Текст сообщения
                          │
9. [Cooldown Set] ────────► Устанавливаем cooldown для правила
```

### 3. **Типы мониторинга**

#### A. **Мониторинг изменений (Change Detection)**
```sql
-- Отслеживает последний статус заказа
SELECT status FROM orders ORDER BY created_at DESC LIMIT 1
```
**Правило:** `value_changed` → уведомление при любом изменении

#### B. **Мониторинг застревания (Stuck Detection)**  
```sql
-- Проверяет активность системы
SELECT last_heartbeat FROM system_health WHERE service = 'api'
```
**Правило:** `value_unchanged` (3600с) → уведомление если значение не меняется час

#### C. **Пороговый мониторинг (Threshold Detection)**
```sql  
-- Контролирует нагрузку
SELECT cpu_usage FROM system_metrics ORDER BY timestamp DESC LIMIT 1
```
**Правило:** `value_greater` (80) → уведомление при превышении 80%

#### D. **Бизнес-логика (Business Rules)**
```sql
-- Сложные бизнес-метрики
SELECT COUNT(*) FROM failed_transactions WHERE created_at > NOW() - INTERVAL '5 minutes'
```
**Правило:** `custom` → `int(new_value) > 10 and old_value != new_value`

### 4. **Анти-спам система**

```
Правило: "CPU > 80%"
Cooldown: 300 секунд (5 минут)

09:00:00 - CPU = 85% ──► 🚨 Отправляем уведомление
09:00:30 - CPU = 87% ──► ⏳ В cooldown, пропускаем  
09:01:00 - CPU = 89% ──► ⏳ В cooldown, пропускаем
09:05:00 - CPU = 91% ──► 🚨 Cooldown истек, отправляем
09:05:30 - CPU = 75% ──► 📉 Изменение, но условие не выполнено
09:06:00 - CPU = 82% ──► 🚨 Новое превышение, отправляем
```

### 5. **Веб-интерфейс синхронизация**

```
┌─ Web Browser ─────────────────────────────┐
│  Vue.js App (localhost:8090)              │
│                                           │
│  Dashboard ◄─┬─ GET /api/stats ◄──────────┼─┐
│  Rules     ◄─┼─ GET /api/rules ◄──────────┼─┤
│  Monitors  ◄─┼─ GET /api/monitors ◄───────┼─┤ FastAPI Server
│  History   ◄─┼─ GET /api/history ◄────────┼─┤
│              └─ POST /api/rules ◄─────────┼─┘
└───────────────────────────────────────────┘
                                           │
                                           ▼
┌─ Main Application ────────────────────────┐
│  ┌─ Database Monitors ─┐                 │
│  │ • monitor_states    │ ◄─────────────┐ │
│  │ • last_values       │               │ │  
│  └─────────────────────┘               │ │
│                                        │ │
│  ┌─ Rules Engine ──────┐               │ │
│  │ • notification_rules│               │ │
│  │ • cooldown_timers   │               │ │
│  └─────────────────────┘               │ │
│                                        │ │
│  ┌─ Sync Task ─────────────────────────┼─┘
│  │ Каждые 30 секунд синхронизирует     │
│  │ состояния между компонентами        │
│  └─────────────────────────────────────┘
└───────────────────────────────────────────┘
```

## 🔍 Диагностика и отладка

### Debug API
```bash
# Информация о состоянии системы
curl http://localhost:8090/api/debug

# Просмотр текущих мониторов  
curl http://localhost:8090/api/monitors

# Статистика уведомлений
curl http://localhost:8090/api/stats
```

### Логи
```bash
# Основные логи приложения
tail -f logs/app.log

# Веб-сервер логи (в консоли)
# INFO: 127.0.0.1:55936 - "GET /api/monitors HTTP/1.1" 200 OK
```

### Типичные проблемы:

1. **"Monitors пустые"** → Проверьте подключение к БД и синхронизацию
2. **"Уведомления не приходят"** → Проверьте активность правил и cooldown
3. **"Telegram бот не отвечает"** → Проверьте токен и авторизацию чатов

## 🚀 Развертывание в продакшене

### Docker (рекомендуемый способ)
```dockerfile
FROM python:3.11-slim

# Установка Java для JDBC
RUN apt-get update && apt-get install -y openjdk-11-jre-headless

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8090

CMD ["python", "main.py"]
```

### Systemd сервис
```ini
[Unit]
Description=Database Monitoring System
After=network.target

[Service]
Type=simple
User=monitoring
WorkingDirectory=/opt/db-monitor
ExecStart=/opt/db-monitor/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Nginx reverse proxy
```nginx
server {
    listen 80;
    server_name monitor.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8090;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📄 Лицензия

MIT License - свободное использование для любых целей.

## 🤝 Поддержка

Для вопросов и предложений создавайте Issues в репозитории.

---

**Автор:** Database Monitoring System Team  
**Версия:** 2.0 (Smart Notifications Edition)  
**Дата обновления:** 2025