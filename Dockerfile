FROM salehmir/jesse:latest

WORKDIR /home

# Устанавливаем системные пакеты
RUN apt-get update && \
    apt-get install -y git netcat-openbsd curl python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Копируем наши файлы
COPY . /home/

# Устанавливаем Python зависимости для ИИ и Telegram
RUN pip3 install --no-cache-dir --root-user-action=ignore \
    python-telegram-bot>=20.0 \
    openai>=1.0.0 \
    aiohttp>=3.8.0 \
    asyncio-mqtt \
    redis>=4.5.0 \
    pydantic>=2.0.0 \
    pandas>=1.5.0 \
    numpy>=1.24.0 \
    structlog \
    python-dotenv

# ИСПРАВЛЕНО: Создаем ПРАВИЛЬНУЮ версию bot_runner.py
COPY <<EOF /home/bot_runner_fixed.py
import os
import logging
from telegram.ext import Application, CommandHandler
from datetime import datetime

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/tmp/telegram_bot_simple.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

async def command_start(update, context):
    logger = logging.getLogger(__name__)
    try:
        logger.info(f"🚀 /start от {update.effective_user.username}")
        
        await update.message.reply_text(
            "🤖 <b>AI Trading Bot активен!</b>\\n\\n"
            "✅ Бот работает\\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}\\n\\n"
            "Отправьте /help для справки",
            parse_mode='HTML'
        )
        logger.info("✅ Ответ отправлен")
    except Exception as e:
        logger.error(f"❌ Ошибка /start: {e}")

async def command_help(update, context):
    await update.message.reply_text("📖 Справка\\n\\n/start - Запуск\\n/help - Справка")

def main():
    logger = setup_logging()
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден")
        return
    
    logger.info("🤖 Запуск бота...")
    
    try:
        application = Application.builder().token(bot_token).build()
        application.add_handler(CommandHandler("start", command_start))
        application.add_handler(CommandHandler("help", command_help))
        
        logger.info("✅ Обработчики добавлены")
        
        # ИСПРАВЛЕНИЕ: НЕ используем asyncio.run()!
        logger.info("🚀 Запускаем polling...")
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
EOF

# Стартовый скрипт с ОТКЛЮЧЕНИЕМ Telegram бота если он ломается
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "⚖️  Создание Jesse проекта для BALANCED TRADER..."\n\
git clone https://github.com/jesse-ai/project-template mybot\n\
cd mybot\n\
\n\
cp /home/.env .\n\
cp /home/routes.py .\n\
cp /home/plugins.py . 2>/dev/null || echo "plugins = []" > plugins.py\n\
\n\
# Копируем все файлы проекта\n\
if [ -d "/home/strategies" ]; then\n\
    rm -rf strategies\n\
    cp -r /home/strategies .\n\
    echo "✅ Стратегии скопированы:"\n\
    ls -la strategies/\n\
else\n\
    echo "❌ Папка стратегий не найдена!"\n\
fi\n\
\n\
# Копируем AI анализ и уведомления\n\
cp -r /home/ai_analysis . 2>/dev/null || echo "⚠️  AI analysis не найден"\n\
cp -r /home/notifications . 2>/dev/null || echo "⚠️  Notifications не найден"\n\
cp -r /home/utils . 2>/dev/null || echo "⚠️  Utils не найден"\n\
cp /home/enhanced_strategy_base.py . 2>/dev/null || echo "⚠️  Enhanced strategy base не найден"\n\
\n\
# ИСПРАВЛЕНИЕ: Копируем ПРАВИЛЬНЫЙ bot_runner\n\
cp /home/bot_runner_fixed.py ./bot_runner.py\n\
echo "✅ Исправленный bot_runner скопирован"\n\
\n\
cp /home/market_analyzer.py . 2>/dev/null || echo "⚠️  Market analyzer не найден"\n\
\n\
echo "📖 Загружаем переменные из .env..."\n\
if [ -f ".env" ]; then\n\
    export $(grep -v "^#" .env | grep -v "^$" | xargs)\n\
    echo "POSTGRES_HOST=$POSTGRES_HOST"\n\
    echo "REDIS_HOST=$REDIS_HOST"\n\
    echo "TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:0:10}..."\n\
    echo "OPENAI_API_KEY=${OPENAI_API_KEY:0:10}..."\n\
else\n\
    echo "❌ .env файл не найден!"\n\
    exit 1\n\
fi\n\
\n\
echo "🔑 === API ДИАГНОСТИКА ==="\n\
if [ -n "$BYBIT_USDT_PERPETUAL_TESTNET_API_KEY" ]; then\n\
    echo "✅ API ключи найдены!"\n\
    curl_result=$(curl -s -w "%{http_code}" "https://api-testnet.bybit.com/v5/market/time" -o /tmp/bybit_test.txt)\n\
    if [ "$curl_result" = "200" ]; then\n\
        echo "✅ Bybit testnet доступен"\n\
    else\n\
        echo "❌ Bybit testnet недоступен (код: $curl_result)"\n\
    fi\n\
else\n\
    echo "❌ API ключи не найдены"\n\
fi\n\
\n\
echo "⏳ Проверка базы данных..."\n\
nc -z $POSTGRES_HOST $POSTGRES_PORT && echo "✅ PostgreSQL доступен" || echo "⚠️ PostgreSQL недоступен"\n\
nc -z $REDIS_HOST $REDIS_PORT && echo "✅ Redis доступен" || echo "⚠️ Redis недоступен"\n\
\n\
echo "🤖 === ЗАПУСК TELEGRAM БОТА ==="\n\
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then\n\
    echo "✅ Telegram конфигурация найдена"\n\
    echo "Bot Token: ${TELEGRAM_BOT_TOKEN:0:10}..."\n\
    echo "Chat ID: $TELEGRAM_CHAT_ID"\n\
    echo ""\n\
    echo "🚀 Пытаемся запустить Telegram бота..."\n\
    \n\
    # ИСПРАВЛЕНИЕ: Пытаемся запустить бота, но НЕ останавливаем Jesse если он сломается\n\
    python3 bot_runner.py > /tmp/telegram_bot_startup.log 2>&1 &\n\
    TELEGRAM_PID=$!\n\
    echo "📱 Telegram бот запущен с PID: $TELEGRAM_PID"\n\
    \n\
    # Ждем 5 секунд и проверяем\n\
    sleep 5\n\
    if kill -0 $TELEGRAM_PID 2>/dev/null; then\n\
        echo "✅ Telegram бот работает стабильно"\n\
        \n\
        # УПРОЩЕННЫЙ мониторинг - проверяем раз в минуту, но НЕ перезапускаем если Jesse работает\n\
        (\n\
          while true; do\n\
            sleep 60\n\
            if [ -n "$TELEGRAM_PID" ]; then\n\
              if kill -0 $TELEGRAM_PID 2>/dev/null; then\n\
                echo "✅ $(date +%H:%M:%S) - Telegram бот работает"\n\
              else\n\
                echo "⚠️ $(date +%H:%M:%S) - Telegram бот остановлен, но Jesse продолжает работать"\n\
                # НЕ перезапускаем! Просто логируем\n\
                TELEGRAM_PID=""\n\
              fi\n\
            fi\n\
          done\n\
        ) &\n\
        \n\
    else\n\
        echo "❌ Telegram бот не запустился, но это НЕ критично!"\n\
        echo "📋 Логи запуска:"\n\
        cat /tmp/telegram_bot_startup.log\n\
        echo ""\n\
        echo "🎯 Jesse будет работать БЕЗ Telegram уведомлений"\n\
    fi\n\
else\n\
    echo "⚠️ Telegram не настроен - работаем БЕЗ уведомлений"\n\
fi\n\
\n\
echo ""\n\
echo "⚖️  === ЗАПУСК BALANCED TRADER ==="\n\
echo "🎯 ЦЕЛЬ: ЗОЛОТАЯ СЕРЕДИНА!"\n\
echo "📊 Стратегия: Сбалансированная торговля"\n\
echo "🤖 ИИ анализ: Включен"\n\
echo "📱 Telegram: Опционально"\n\
echo ""\n\
echo "🔍 === ФИНАЛЬНАЯ ПРОВЕРКА СИСТЕМЫ ==="\n\
echo "📊 Jesse: Готов к запуску"\n\
if [ -n "$TELEGRAM_PID" ] && kill -0 $TELEGRAM_PID 2>/dev/null; then\n\
    echo "📱 Telegram: ✅ Работает (PID: $TELEGRAM_PID)"\n\
else\n\
    echo "📱 Telegram: ⚠️  Отключен (Jesse работает независимо)"\n\
fi\n\
if [ -n "$OPENAI_API_KEY" ]; then\n\
    echo "🤖 AI Analysis: ✅ Включен"\n\
else\n\
    echo "🤖 AI Analysis: ❌ Отключен"\n\
fi\n\
echo ""\n\
echo "🎯 Основная система готова! Запускаем Jesse..."\n\
echo ""\n\
\n\
# ГЛАВНОЕ: Запускаем Jesse независимо от статуса Telegram бота\n\
exec jesse run\n\
' > /setup_and_run.sh && chmod +x /setup_and_run.sh

# Экспонируем порт (для Jesse web interface)
EXPOSE 9000

CMD ["/setup_and_run.sh"]
