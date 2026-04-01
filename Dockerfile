FROM python:3.11-slim

# 📁 рабочая папка
WORKDIR /app

# 📦 копируем зависимости
COPY requirements.txt .

# 📥 установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# 📁 копируем проект
COPY . .

# 🚀 запуск бота
CMD ["python", "main.py"]