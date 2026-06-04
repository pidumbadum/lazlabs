#загрузка урезанного образа питона
FROM python:3.11-slim 

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

#Если папки /app не существует, WORKDIR создаст её автоматически.
WORKDIR /app 

#Сначала копируем и устанавливаем core-пакет (слой кэшируется, если core не меняется)
COPY packages/core /app/packages/core
RUN pip install --no-cache-dir -e /app/packages/core

#Копируем зависимости приложения
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

#Копируем код приложения и скрипты
COPY app/app /app/app
COPY scripts /app/scripts

#Создаем папку для БД и даем права на запись (важно для SQLite)
RUN mkdir -p /app/data && chmod 777 /app/data

# Переменные окружения
ENV DATABASE_PATH=/app/data/school.db
ENV FLASK_APP=app.main:app
ENV FLASK_ENV=production

EXPOSE 5000

# Healthcheck для проверки готовности приложения
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/login || exit 1

CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]