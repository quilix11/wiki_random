#!/bin/bash

# Скрипт для автоматичного розгортання бота на Oracle Cloud VPS (Ubuntu/Debian)

echo "🚀 Починаємо розгортання Wiki Quiz Bot на Oracle Cloud..."

# 1. Оновлення системи
echo "🔄 Оновлення пакетів..."
sudo apt-get update && sudo apt-get upgrade -y

# 2. Встановлення Docker та Docker Compose (якщо ще немає)
if ! command -v docker &> /dev/null
then
    echo "🐳 Встановлення Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
fi

if ! command -v docker-compose &> /dev/null
then
    echo "🐙 Встановлення Docker Compose..."
    sudo apt-get install -y docker-compose
fi

# 3. Створення необхідних папок
echo "📁 Створення структури папок..."
mkdir -p ~/wiki_quiz/database

# 4. Перевірка наявності файлів (якщо скрипт запущено в папці з проектом)
if [ -f "docker-compose.yml" ]; then
    echo "📄 Копіювання конфігурацій..."
    cp docker-compose.yml ~/wiki_quiz/
    cp Dockerfile ~/wiki_quiz/
    cp requirements.txt ~/wiki_quiz/
    # Копіюємо всі інші папки
    cp -r database services telegram_bot ~/wiki_quiz/
fi

cd ~/wiki_quiz

# 5. Перевірка .env файлу
if [ ! -f ".env" ]; then
    echo "⚠️ Файл .env не знайдено!"
    echo "Введіть TELEGRAM_TOKEN:"
    read token
    echo "Введіть API_KEY (Gemini):"
    read api_key
    
    echo "TELEGRAM_TOKEN=$token" > .env
    echo "API_KEY=$api_key" >> .env
    echo "DATABASE_URL=/app/database/wiki_quiz.db" >> .env
    echo "✅ Файл .env створено."
fi

# 6. Запуск контейнера
echo "🏗️ Збірка та запуск контейнера..."
sudo docker-compose up -d --build

echo "✅ Бот успішно запущений 24/7!"
echo "Ви можете перевірити статус командою: sudo docker ps"
echo "Переглянути логи: sudo docker logs -f wiki_quiz_bot"
