# Используем официальный Python образ
FROM python:3.12.12-slim-bookworm

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    openjdk-17-jdk \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код приложения
COPY . .

# Создаем директории для логов и базы данных
RUN mkdir -p logs data

# Устанавливаем переменные окружения для Java
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# Копируем и настраиваем entrypoint скрипт
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Открываем порт для веб-интерфейса
EXPOSE 8090

# Устанавливаем entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
