# Makefile для управления Database Monitor Telegram Bot

# Переменные
COMPOSE_FILE = docker-compose.yml
SERVICE_NAME = migr-telegram

.PHONY: help setup build up down restart logs status clean test

# По умолчанию показываем справку
help:
	@echo "🐳 Database Monitor Telegram Bot - Docker Management"
	@echo ""
	@echo "Доступные команды:"
	@echo "  setup     - Создать необходимые директории"
	@echo "  build     - Собрать Docker образ"
	@echo "  up        - Запустить приложение"
	@echo "  down      - Остановить приложение"
	@echo "  restart   - Перезапустить приложение"
	@echo "  logs      - Показать логи"
	@echo "  status    - Показать статус контейнеров"
	@echo "  test      - Протестировать API"
	@echo "  clean     - Очистить Docker ресурсы"
	@echo ""
	@echo "Примеры:"
	@echo "  make setup   # Подготовка директорий"
	@echo "  make up      # Запуск приложения"
	@echo "  make logs    # Просмотр логов"

# Подготовка окружения
setup:
	@echo "📁 Создание необходимых директорий..."
	@mkdir -p logs data lib
	@touch logs/.gitkeep data/.gitkeep
	@echo "✅ Директории созданы"
	@echo ""
	@echo "🔧 Следующие шаги:"
	@echo "1. Поместите postgresql.jar в lib/"
	@echo "2. Скопируйте .env.example в .env и заполните"
	@echo "3. Проверьте config.yaml"
	@echo "4. Запустите: make up"

# Сборка образа
build:
	@echo "🔨 Сборка Docker образа..."
	docker-compose build

# Запуск приложения
up:
	@echo "🚀 Запуск приложения..."
	docker-compose up -d
	@echo "✅ Приложение запущено"
	@echo "🌐 Веб-интерфейс: http://localhost:8090"

# Остановка приложения
down:
	@echo "⏹️  Остановка приложения..."
	docker-compose down

# Перезапуск
restart:
	@echo "🔄 Перезапуск приложения..."
	docker-compose restart

# Просмотр логов
logs:
	@echo "📋 Логи приложения:"
	docker-compose logs -f $(SERVICE_NAME)

# Статус контейнеров
status:
	@echo "📊 Статус контейнеров:"
	docker-compose ps

# Тестирование API
test:
	@echo "🧪 Тестирование API..."
	@curl -s http://localhost:8090/api/stats || echo "❌ API недоступен"
	@curl -s http://localhost:8090/api/rules | jq '.[] | {name: .name, active: .is_active}' 2>/dev/null || echo "📋 Правила недоступны"

# Очистка Docker ресурсов
clean:
	@echo "🧹 Очистка Docker ресурсов..."
	docker-compose down -v
	docker system prune -f
	@echo "✅ Очистка завершена"

# Обновление и пересборка
update:
	@echo "🔄 Обновление приложения..."
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d
	@echo "✅ Приложение обновлено"

# Вход в контейнер
shell:
	@echo "🐚 Вход в контейнер..."
	docker-compose exec $(SERVICE_NAME) bash

# Проверка health
health:
	@echo "❤️  Проверка здоровья..."
	docker-compose exec $(SERVICE_NAME) curl -f http://localhost:8090/api/stats

# Backup данных
backup:
	@echo "💾 Создание backup..."
	@tar -czf backup-$(shell date +%Y%m%d-%H%M%S).tar.gz logs/ data/
	@echo "✅ Backup создан"