# 🐳 Запуск приложения в Docker

## 📋 Предварительные требования

1. **Docker** и **Docker Compose** установлены
2. **JDBC драйвер PostgreSQL** в папке `lib/postgresql.jar`
3. **Telegram Bot Token** (получить у @BotFather)
4. **Доступ к базе данных PostgreSQL**

## 🚀 Быстрый запуск

### 1. Подготовка конфигурации

```bash
# Скопируйте пример файла окружения
cp .env.example .env

# Отредактируйте .env файл
nano .env
```

### 2. Заполните .env файл

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
TELEGRAM_ADMIN_USER_ID=123456789

# Database Configuration  
DATABASE_URL=jdbc:postgresql://migration.vrn:2532/migration
DATABASE_USER=tomcat
DATABASE_PASSWORD=password

# Logging
LOG_LEVEL=INFO

# Application Settings
WEB_PORT=8090
```

### 3. Подготовка директорий

```bash
# Создайте необходимые директории
mkdir -p logs data lib

# Убедитесь что JDBC драйвер на месте
ls -la lib/postgresql.jar
```

### 4. Запуск приложения

```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Проверка статуса
docker-compose ps
```

## 📊 Проверка работы

### Веб-интерфейс
```bash
# Откройте в браузере
http://localhost:8090
```

### API проверки
```bash
# Проверка статуса
curl http://localhost:8090/api/stats

# Проверка правил
curl http://localhost:8090/api/rules

# Проверка мониторов
curl http://localhost:8090/api/monitors
```

### Health Check
```bash
# Проверка здоровья контейнера
docker-compose exec migr-telegram curl -f http://localhost:8090/api/stats
```

## 🔧 Управление контейнером

### Основные команды

```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Просмотр логов
docker-compose logs -f migr-telegram

# Вход в контейнер
docker-compose exec migr-telegram bash

# Пересборка образа
docker-compose build --no-cache
```

### Обновление приложения

```bash
# Остановить приложение
docker-compose down

# Собрать новый образ
docker-compose build

# Запустить обновленное приложение
docker-compose up -d
```

## 📁 Структура volumes

```
./logs/          -> /app/logs           # Логи приложения
./data/          -> /app/data           # SQLite база уведомлений  
./lib/           -> /app/lib            # JDBC драйверы
./config.yaml    -> /app/config.yaml    # Конфигурация
```

## 🐛 Диагностика проблем

### Проверка логов

```bash
# Логи приложения
docker-compose logs migr-telegram

# Логи с последними 100 строками
docker-compose logs --tail=100 migr-telegram

# Следить за логами в реальном времени
docker-compose logs -f migr-telegram
```

### Проверка конфигурации

```bash
# Проверить переменные окружения
docker-compose exec migr-telegram env | grep TELEGRAM
docker-compose exec migr-telegram env | grep DATABASE

# Проверить конфигурационный файл
docker-compose exec migr-telegram cat /app/config.yaml
```

### Проверка сети

```bash
# Проверить соединение с базой данных из контейнера
docker-compose exec migr-telegram ping migration.vrn

# Проверить порты
docker-compose exec migr-telegram netstat -tlnp
```

### Проверка файлов

```bash
# Проверить JDBC драйвер
docker-compose exec migr-telegram ls -la /app/lib/

# Проверить логи
docker-compose exec migr-telegram ls -la /app/logs/

# Проверить базу данных уведомлений
docker-compose exec migr-telegram ls -la /app/data/
```

## 🔄 Автозапуск при перезагрузке

Контейнер настроен с `restart: unless-stopped`, что означает:
- Автоматический запуск при загрузке системы
- Перезапуск при падении приложения
- Остановка только при ручной команде `docker-compose down`

## 📱 Настройка Telegram бота

После запуска приложения:

1. **Найдите своего бота** в Telegram
2. **Отправьте команду** `/start`
3. **Используйте команды**:
   - `/help` - справка
   - `/status` - статус мониторинга
   - `/list` - список мониторов
   - `/test_rules` - тестирование правил (только админ)

## 🚨 Важные моменты

1. **Безопасность**: Не коммитьте `.env` файл в Git
2. **Backup**: Регулярно сохраняйте папки `data/` и `logs/`
3. **Мониторинг**: Используйте `docker-compose logs` для отслеживания проблем
4. **Обновления**: При обновлении кода пересобирайте образ Docker

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose logs -f`
2. Проверьте health check: `docker-compose ps`
3. Проверьте конфигурацию: переменные окружения и config.yaml
4. Проверьте сетевое соединение с базой данных