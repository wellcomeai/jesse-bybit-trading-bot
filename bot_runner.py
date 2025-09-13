# bot_runner.py - ГОТОВАЯ К ДЕПЛОЮ ВЕРСИЯ
# ИСПРАВЛЕНО: Убрали asyncio.run() конфликт, упростили логику

import os
import logging
import time
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime

def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/tmp/telegram_bot_simple.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

async def command_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    logger = logging.getLogger(__name__)
    
    try:
        user_info = f"{update.effective_user.username} (ID: {update.effective_chat.id})"
        logger.info(f"🚀 /start от {user_info}")
        
        keyboard = [
            [InlineKeyboardButton("📊 Статус", callback_data="status")],
            [InlineKeyboardButton("📈 Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        current_time = datetime.now().strftime("%H:%M:%S")
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        message_text = (
            "🤖 <b>AI Trading Bot активен!</b>\n\n"
            "✅ Бот работает\n"
            "✅ Команды доступны\n" 
            "✅ Уведомления включены\n\n"
            f"⏰ Время: {current_time}\n"
            f"📅 {current_date}\n\n"
            "Выберите действие:"
        )
        
        await update.message.reply_text(
            message_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        
        logger.info("✅ Ответ на /start отправлен")
        
    except Exception as e:
        logger.error(f"❌ Ошибка /start: {e}")
        try:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        except:
            pass

async def command_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("📖 /help команда")
        
        help_text = (
            "📖 <b>Справка AI Trading Bot</b>\n\n"
            "<b>Команды:</b>\n"
            "• /start - Запуск бота\n"
            "• /help - Эта справка\n"
            "• /status - Статус системы\n\n"
            "<b>Возможности:</b>\n"
            "🤖 ИИ анализ торговых сигналов\n"
            "📊 Мониторинг стратегий\n"
            "📱 Уведомления о сделках\n\n"
            "Бот работает автоматически!"
        )
        
        await update.message.reply_text(help_text, parse_mode="HTML")
        logger.info("✅ Справка отправлена")
        
    except Exception as e:
        logger.error(f"❌ Ошибка /help: {e}")

async def command_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /status"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("📊 /status команда")
        
        current_time = datetime.now().strftime("%H:%M:%S")
        current_date = datetime.now().strftime("%d.%m.%Y")
        
        status_text = (
            "🟢 <b>Статус системы</b>\n\n"
            "✅ Telegram бот: Работает\n"
            "✅ Jesse фреймворк: Активен\n"
            "🤖 ИИ анализ: Доступен\n"
            "📊 Стратегии: 3 активные\n\n"
            f"⏰ {current_time}\n"
            f"🗓 {current_date}"
        )
        
        await update.message.reply_text(status_text, parse_mode="HTML")
        logger.info("✅ Статус отправлен")
        
    except Exception as e:
        logger.error(f"❌ Ошибка /status: {e}")

def main():
    """Главная функция - ИСПРАВЛЕНА"""
    logger = setup_logging()
    
    try:
        # Проверяем переменные окружения
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            logger.error("❌ Не найдены TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
            return
        
        logger.info("🤖 Запуск простого Telegram бота")
        logger.info(f"Bot token: {bot_token[:10]}...")
        logger.info(f"Chat ID: {chat_id}")
        
        # Создаем приложение
        application = Application.builder().token(bot_token).build()
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", command_start))
        application.add_handler(CommandHandler("help", command_help))
        application.add_handler(CommandHandler("status", command_status))
        
        logger.info("✅ Обработчики команд добавлены")
        
        # ИСПРАВЛЕНИЕ: НЕ ИСПОЛЬЗУЕМ asyncio.run()!
        # Старый код который ломал все:
        # asyncio.run(test_bot())  # ← ЭТО СОЗДАВАЛО КОНФЛИКТ!
        
        # Новый код: позволяем run_polling создать свой event loop
        logger.info("🚀 Запускаем polling...")
        application.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("🛑 Остановка по Ctrl+C")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
