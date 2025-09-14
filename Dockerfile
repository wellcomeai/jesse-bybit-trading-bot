FROM salehmir/jesse:latest

WORKDIR /home

# Устанавливаем системные пакеты
RUN apt-get update && \
    apt-get install -y git netcat-openbsd curl python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Копируем наши файлы (включая bot_runner.py)
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

# Стартовый скрипт с использованием готового bot_runner.py
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "⚖️  Создание Jesse проекта для BALANCED TRADER..."\n\
git clone https://github.com/jesse-ai/project-template mybot\n\
cd mybot\n\
\n\
# Копируем конфигурационные файлы\n\
cp /home/.env .\n\
cp /home/routes.py .\n\
cp /home/plugins.py . 2>/dev/null || echo "plugins = []" > plugins.py\n\
\n\
# Копируем все компоненты проекта\n\
echo "📁 Копирование компонентов проекта..."\n\
[ -d "/home/strategies" ] && { rm -rf strategies && cp -r /home/strategies . && echo "✅ Стратегии скопированы"; } || echo "❌ Стратегии не найдены"\n\
[ -d "/home/ai_analysis" ] && { cp -r /home/ai_analysis . && echo "✅ AI анализ скопирован"; } || echo "⚠️  AI анализ не найден"\n\
[ -d "/home/notifications" ] && { cp -r /home/notifications . && echo "✅ Уведомления скопированы"; } || echo "⚠️  Уведомления не найдены"\n\
[ -d "/home/utils" ] && { cp -r /home/utils . && echo "✅ Утилиты скопированы"; } || echo "⚠️  Утилиты не найдены"\n\
[ -f "/home/enhanced_strategy_base.py" ] && { cp /home/enhanced_strategy_base.py . && echo "✅ Enhanced strategy base скопирован"; } || echo "⚠️  Enhanced strategy base не найден"\n\
[ -f "/home/market_analyzer.py" ] && { cp /home/market_analyzer.py . && echo "✅ Market analyzer скопирован"; } || echo "⚠️  Market analyzer не найден"\n\
\n\
# ПРОСТО КОПИРУЕМ ГОТОВЫЙ bot_runner.py\n\
if [ -f "/home/bot_runner.py" ]; then\n\
    cp /home/bot_runner.py .\n\
    echo "✅ bot_runner.py скопирован из проекта"\n\
    ls -la bot_runner.py\n\
else\n\
    echo "❌ bot_runner.py НЕ НАЙДЕН в проекте!"\n\
    echo "📋 Доступные файлы в /home:"\n\
    ls -la /home/*.py\n\
fi\n\
\n\
echo "📖 Загружаем переменные из .env (БЕЗ ПЕРЕЗАПИСИ)..."\n\
if [ -f ".env" ]; then\n\
    # ИСПРАВЛЕНО: Загружаем только отсутствующие переменные\n\
    while IFS= read -r line; do\n\
        if [[ $line =~ ^[A-Z_]+=.* ]] && [[ ! $line =~ ^# ]]; then\n\
            var_name=$(echo "$line" | cut -d= -f1)\n\
            if [[ -z "${!var_name}" ]]; then\n\
                export "$line"\n\
                echo "  ✅ Загружена из .env: $var_name"\n\
            else\n\
                echo "  ⏩ Пропущена (уже установлена): $var_name=${!var_name:0:10}..."\n\
            fi\n\
        fi\n\
    done < .env\n\
    \n\
    echo "📋 Итоговые переменные:"\n\
    echo "POSTGRES_HOST=$POSTGRES_HOST"\n\
    echo "REDIS_HOST=$REDIS_HOST" \n\
    echo "TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:0:10}..."\n\
    echo "OPENAI_API_KEY=${OPENAI_API_KEY:0:10}... (приоритет: $([ -n "$OPENAI_API_KEY" ] && echo "системная переменная" || echo ".env файл"))"\n\
else\n\
    echo "❌ .env файл не найден!"\n\
    exit 1\n\
fi\n\
\n\
echo "🔑 === API ДИАГНОСТИКА ==="\n\
if [ -n "$BYBIT_USDT_PERPETUAL_TESTNET_API_KEY" ]; then\n\
    echo "✅ Bybit API ключи найдены!"\n\
    curl_result=$(curl -s -w "%{http_code}" "https://api-testnet.bybit.com/v5/market/time" -o /tmp/bybit_test.txt 2>/dev/null)\n\
    if [ "$curl_result" = "200" ]; then\n\
        echo "✅ Bybit testnet доступен"\n\
    else\n\
        echo "⚠️ Bybit testnet недоступен (код: $curl_result)"\n\
    fi\n\
else\n\
    echo "⚠️ Bybit API ключи не найдены"\n\
fi\n\
\n\
echo "⏳ Проверка сетевых подключений..."\n\
nc -z $POSTGRES_HOST $POSTGRES_PORT && echo "✅ PostgreSQL доступен" || echo "⚠️ PostgreSQL недоступен"\n\
nc -z $REDIS_HOST $REDIS_PORT && echo "✅ Redis доступен" || echo "⚠️ Redis недоступен"\n\
\n\
echo ""\n\
echo "🤖 === ЗАПУСК TELEGRAM БОТА ==="\n\
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then\n\
    echo "✅ Telegram конфигурация найдена"\n\
    echo "📱 Bot Token: ${TELEGRAM_BOT_TOKEN:0:10}..."\n\
    echo "💬 Chat ID: $TELEGRAM_CHAT_ID"\n\
    \n\
    if [ -f "bot_runner.py" ]; then\n\
        echo "🚀 Запускаем готовый bot_runner.py..."\n\
        \n\
        # ЗАПУСКАЕМ ГОТОВЫЙ ФАЙЛ\n\
        python3 bot_runner.py > /tmp/telegram_bot.log 2>&1 &\n\
        TELEGRAM_PID=$!\n\
        echo "📱 Telegram бот запущен с PID: $TELEGRAM_PID"\n\
        \n\
        # Проверяем запуск\n\
        sleep 5\n\
        if kill -0 $TELEGRAM_PID 2>/dev/null; then\n\
            echo "✅ Telegram бот работает стабильно!"\n\
            echo "🎯 Доступные команды: /start, /help, /status"\n\
            echo "🔘 Интерактивные кнопки активны"\n\
            \n\
            # Простой мониторинг в фоне\n\
            (\n\
                while true; do\n\
                    sleep 120  # Проверяем каждые 2 минуты\n\
                    if [ -n "$TELEGRAM_PID" ] && kill -0 $TELEGRAM_PID 2>/dev/null; then\n\
                        echo "✅ $(date +%H:%M:%S) - Telegram бот активен"\n\
                    else\n\
                        echo "⚠️ $(date +%H:%M:%S) - Telegram бот остановился"\n\
                        [ -f /tmp/telegram_bot.log ] && { echo "📋 Последние логи:"; tail -n 5 /tmp/telegram_bot.log; }\n\
                        TELEGRAM_PID=""\n\
                        break\n\
                    fi\n\
                done\n\
            ) &\n\
        else\n\
            echo "❌ Telegram бот НЕ запустился!"\n\
            echo "📋 Логи ошибок:"\n\
            cat /tmp/telegram_bot.log 2>/dev/null || echo "Логи недоступны"\n\
            echo "🎯 Продолжаем без Telegram бота"\n\
        fi\n\
    else\n\
        echo "❌ bot_runner.py НЕ НАЙДЕН! Пропускаем Telegram бота"\n\
    fi\n\
else\n\
    echo "⚠️ Telegram не настроен (отсутствуют токены)"\n\
    echo "🎯 Работаем БЕЗ Telegram уведомлений"\n\
fi\n\
\n\
echo ""\n\
echo "⚖️  === ФИНАЛЬНЫЙ ЗАПУСК ==="\n\
echo "🎯 Система готова к торговле!"\n\
echo "📊 Jesse Framework: готов"\n\
if [ -n "$TELEGRAM_PID" ] && kill -0 $TELEGRAM_PID 2>/dev/null; then\n\
    echo "📱 Telegram бот: ✅ активен (PID: $TELEGRAM_PID)"\n\
else\n\
    echo "📱 Telegram бот: ⚠️ не активен"\n\
fi\n\
echo "🤖 AI анализ: $([ "$AI_ANALYSIS_ENABLED" = "true" ] && echo "✅ включен" || echo "⚠️ отключен")"\n\
echo "🔄 Стратегии: 3 готовы к запуску"\n\
echo ""\n\
echo "🚀 Запускаем Jesse..."\n\
echo "═══════════════════════════════════════════════════════════"\n\
\n\
# ГЛАВНОЕ: Запускаем Jesse\n\
exec jesse run\n\
' > /setup_and_run.sh && chmod +x /setup_and_run.sh

# Экспонируем порт для Jesse web interface
EXPOSE 9000

CMD ["/setup_and_run.sh"]
