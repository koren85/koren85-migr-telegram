#!/bin/bash

echo "📁 Создание необходимых директорий для Docker..."

# Создаем директории
mkdir -p logs data lib

# Создаем .gitkeep файлы чтобы директории попали в Git
touch logs/.gitkeep
touch data/.gitkeep

echo "✅ Директории созданы:"
echo "📁 logs/     - логи приложения"
echo "📁 data/     - база данных уведомлений SQLite"
echo "📁 lib/      - JDBC драйверы (поместите сюда postgresql.jar)"

echo ""
echo "🔧 Следующие шаги:"
echo "1. Скопируйте JDBC драйвер PostgreSQL в lib/postgresql.jar"
echo "2. Скопируйте .env.example в .env и заполните переменные"
echo "3. Проверьте config.yaml"
echo "4. Запустите: docker-compose up -d"