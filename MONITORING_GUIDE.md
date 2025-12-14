# 📖 Пошаговое руководство по мониторингу базы данных

## 🔧 1. Настройка объекта мониторинга в config.yaml

### Структура конфигурации:

```yaml
databases:
  - name: "имя_базы_данных"           # Уникальное имя для идентификации БД
    driver: "драйвер_jdbc"            # JDBC драйвер (например, org.postgresql.Driver)
    url: "jdbc:postgresql://host:port/db"  # URL подключения к БД
    username: "пользователь"          # Имя пользователя БД
    password: "пароль"               # Пароль для подключения
    jar_path: "путь/к/драйверу.jar"  # Путь к JAR файлу JDBC драйвера
    
    tables:                          # Список объектов для мониторинга
      - name: "уникальное_имя_монитора"     # Имя монитора (отображается в уведомлениях)
        sql_query: "SELECT поле FROM таблица WHERE условие LIMIT 1"  # SQL запрос
        check_interval: 30            # Интервал проверки в секундах
```

### Описание параметров:

- **name** - уникальное имя базы данных (используется в правилах уведомлений)
- **driver** - класс JDBC драйвера:
  - PostgreSQL: `org.postgresql.Driver`
  - MySQL: `com.mysql.cj.jdbc.Driver`
  - Oracle: `oracle.jdbc.driver.OracleDriver`
- **url** - строка подключения JDBC
- **username/password** - учетные данные для БД
- **jar_path** - абсолютный путь к JAR файлу драйвера
- **tables.name** - имя монитора (будет отображаться в уведомлениях)
- **sql_query** - SQL запрос, который должен возвращать ОДНО значение
- **check_interval** - как часто проверять (в секундах)

### Пример реальной конфигурации:

```yaml
databases:
  - name: "voron_migr_db"
    driver: "org.postgresql.Driver"
    url: "jdbc:postgresql://migration.vrn:2532/migration"
    username: "migration"
    password: "migration"
    jar_path: "/Users/aleksandrcernaev/projects/migr-telegram/drivers/postgresql-42.7.4.jar"
    
    tables:
      - name: "bdm_file_task_status"
        sql_query: "SELECT a_status FROM BDM_FILE_TASK bdm3 JOIN cms_task t ON t.ouid=bdm3.ouid LIMIT 1"
        check_interval: 30
        
      - name: "Воронеж 1 задача"
        sql_query: "SELECT a_status FROM BDM_STRUCTURE_TASK bdm1 JOIN cms_task t ON t.ouid=bdm1.ouid LIMIT 1"
        check_interval: 30
```

## 📊 2. Создание правила уведомления

### Типы условий срабатывания:

1. **value_changed** - при любом изменении значения
2. **value_equals** - когда значение равно определенному
3. **value_not_equals** - когда значение НЕ равно определенному
4. **value_contains** - когда значение содержит подстроку
5. **value_greater** - когда значение больше указанного (для чисел)
6. **value_less** - когда значение меньше указанного (для чисел)
7. **value_unchanged** - когда значение не меняется определенное время
8. **custom** - пользовательское Python выражение

### Параметры правила:

- **name** - название правила
- **monitor_name** - имя монитора из config.yaml
- **db_name** - имя базы данных из config.yaml
- **condition_type** - тип условия (см. выше)
- **condition_value** - значение для сравнения (если нужно)
- **condition_duration** - время в секундах (для time-based условий)
- **cooldown_seconds** - пауза между уведомлениями (анти-спам)
- **priority** - приоритет: low, medium, high, critical
- **message_template** - шаблон сообщения
- **target_chats** - "all" или список chat_id через запятую
- **is_active** - включено/выключено правило

### Переменные в шаблоне сообщения:

- `{monitor_name}` - имя монитора
- `{db_name}` - имя базы данных
- `{old_value}` - предыдущее значение
- `{new_value}` - новое значение
- `{timestamp}` - время изменения
- `{same_value_duration}` - время в одном состоянии (для value_unchanged)

### Примеры правил:

#### Правило на изменение значения:
```json
{
  "name": "Воронеж 1 задача - Изменения",
  "monitor_name": "Воронеж 1 задача",
  "db_name": "voron_migr_db", 
  "condition_type": "value_changed",
  "condition_value": null,
  "condition_duration": null,
  "cooldown_seconds": 60,
  "priority": "medium",
  "message_template": "🔄 {monitor_name}: {old_value} → {new_value}",
  "target_chats": "all",
  "is_active": true
}
```

#### Правило на конкретное значение:
```json
{
  "name": "Задача завершена",
  "monitor_name": "bdm_file_task_status",
  "db_name": "voron_migr_db",
  "condition_type": "value_equals",
  "condition_value": "completed",
  "condition_duration": null,
  "cooldown_seconds": 300,
  "priority": "high",
  "message_template": "✅ {monitor_name} завершена!",
  "target_chats": "all",
  "is_active": true
}
```

#### Правило на зависание:
```json
{
  "name": "Воронеж 1 задача - Зависание",
  "monitor_name": "Воронеж 1 задача",
  "db_name": "voron_migr_db",
  "condition_type": "value_unchanged", 
  "condition_value": null,
  "condition_duration": 1800,
  "cooldown_seconds": 3600,
  "priority": "high",
  "message_template": "⚠️ {monitor_name} не меняется уже 30 минут (значение: {new_value})",
  "target_chats": "all",
  "is_active": true
}
```

#### Кастомное правило:
```json
{
  "name": "Ошибка в задаче",
  "monitor_name": "bdm_file_task_status",
  "db_name": "voron_migr_db",
  "condition_type": "custom",
  "condition_value": "new_value in ['error', 'failed', 'exception']",
  "condition_duration": null,
  "cooldown_seconds": 120,
  "priority": "critical",
  "message_template": "🚨 ОШИБКА в {monitor_name}: {new_value}",
  "target_chats": "all",
  "is_active": true
}
```

## 🎯 3. Рекомендации по настройке

### Для надежного мониторинга создавайте ДВА правила для каждого монитора:

1. **На изменение значения** (основное) - отслеживает все изменения
2. **На зависание** (контрольное) - предупреждает о длительном отсутствии изменений

### Настройка приоритетов:

- **low** - информационные сообщения
- **medium** - обычные изменения состояния
- **high** - важные события (ошибки, завершения)
- **critical** - критические проблемы

### Настройка cooldown:

- **Частые изменения** (каждые несколько секунд) - cooldown 60-300 секунд
- **Редкие изменения** (раз в час) - cooldown 60-120 секунд
- **Ошибки** - cooldown 300-600 секунд (чтобы не спамить)

## 🧪 4. Тестирование системы

### Веб-интерфейс (http://localhost:8090):

1. **Панель → "Отправить тестовое уведомление"** 
   - Проверяет отправку в Telegram
   - Симулирует изменение значения

2. **Панель → "Протестировать все правила"**
   - Тестирует все активные правила
   - Показывает количество сработавших

3. **Вкладка "Правила"**
   - Создание/редактирование правил
   - Тестирование отдельных правил

4. **Вкладка "Мониторы"**
   - Текущие значения всех мониторов
   - Время последнего изменения

### Telegram команды:

- `/list` - список всех мониторов
- `/get <db_name> <monitor_name>` - получить текущее значение
- `/status` - статус системы мониторинга
- `/test_rules` - принудительно протестировать правила (только админ)

## 🚨 5. Диагностика проблем

### Почему уведомления не приходят:

1. **Cooldown активен** - проверьте время последнего уведомления
2. **Первое значение** - `value_changed` не сработает для первого чтения
3. **Одинаковые значения** - если БД возвращает то же значение
4. **Ошибки подключения к БД** - проверьте логи
5. **Ошибки Telegram** - проверьте токен бота и chat_id
6. **Неправильные имена** - убедитесь что `monitor_name` и `db_name` совпадают с конфигом

### Частые ошибки:

- **Пустой `monitor_name`** - правило не сработает
- **Неправильный `db_name`** - не найдет монитор
- **SQL запрос возвращает NULL** - монитор не обновится
- **Слишком большой cooldown** - уведомления будут редкими

### Проверка состояния:

1. Откройте веб-интерфейс http://localhost:8090
2. Проверьте вкладку "Мониторы" - видны ли текущие значения
3. Проверьте вкладку "История" - есть ли записи о уведомлениях
4. Используйте кнопки тестирования

## 📱 6. Управление Telegram ботом

### Авторизация:

- Добавьте свой `user_id` в `telegram.admin_user_ids` в config.yaml
- Для групп используйте `/add_group` в нужной группе

### Команды администратора:

- `/add_group` - добавить текущий чат в список уведомлений
- `/groups` - показать все авторизованные чаты
- `/test_rules` - принудительно протестировать все правила

## 🔄 7. Перезапуск и обновления

### После изменения config.yaml:
```bash
# Остановить приложение (Ctrl+C)
# Запустить заново
python main.py
```

### После изменения правил:
- Правила применяются сразу через веб-интерфейс
- Перезапуск не требуется

### Проверка работы:
```bash
# Проверить что приложение запущено
curl http://localhost:8090/api/stats

# Проверить активные правила
curl http://localhost:8090/api/rules?active_only=true

# Проверить состояние мониторов
curl http://localhost:8090/api/monitors
```

---

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи приложения
2. Используйте веб-интерфейс для диагностики
3. Проверьте подключение к БД и Telegram
4. Убедитесь в правильности имен мониторов и БД в правилах