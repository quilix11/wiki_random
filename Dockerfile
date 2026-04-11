FROM python:3.11-slim

# Встановлюємо робочу директорію
WORKDIR /app

# Встановлюємо системні залежності
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копіюємо файл залежностей
COPY requirements.txt .

# Встановлюємо залежності Python
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо всі файли проекту
COPY . .

# Створюємо папку для бази даних та встановлюємо права
# В Koyeb/Render/etc. корінь проекту зазвичай /app
# Ми вказуємо шлях за замовчуванням
ENV DATABASE_URL=/app/database/wiki_quiz.db

# Запускаємо бота
CMD ["python", "telegram_bot/bot.py"]
