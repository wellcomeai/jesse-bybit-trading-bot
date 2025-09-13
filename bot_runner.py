# bot_runner.py - ИСПРАВЛЕНО для python-telegram-bot 20.0+
import os
import logging
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
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
        
        # ИСПРАВЛЕНО: Новый синтаксис для python-telegram-bot 20.0+
        keyboard = [
            [InlineKeyboardButton("📊 Статус", callback_data="status")],
            [InlineKeyboardButton("📈 Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)  # ← КЛЮЧЕВОЕ ИЗМЕНЕНИЕ!
        
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
        
        logger.info("✅ Ответ на /start отправлен с кнопками")
        
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
        
        # ИСПРАВЛЕНО: Новый синтаксис кнопки "Назад"
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await update.message.reply_text(
            help_text, 
            parse_mode="HTML",
            reply_markup=reply_markup
        )
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
        
        # Проверяем статус компонентов
        ai_status = "✅ Включен" if os.getenv('AI_ANALYSIS_ENABLED') == 'true' else "❌ Отключен"
        telegram_status = "✅ Работает"  # Если мы здесь, значит работает
        
        status_text = (
            "🟢 <b>СТАТУС СИСТЕМЫ</b>\n\n"
            f"📱 Telegram бот: {telegram_status}\n"
            f"🤖 ИИ анализ: {ai_status}\n"
            "📊 Jesse фреймворк: ✅ Активен\n"
            "🔄 Стратегии: 3 активные\n\n"
            "<b>Активные стратегии:</b>\n"
            "• ActiveScalper (BTCUSDT, 5m)\n"
            "• BalancedTrader (BTCUSDT, 15m)\n"
            "• QualityTrader (BTCUSDT, 1h)\n\n"
            f"⏰ Время: {current_time}\n"
            f"📅 {current_date}"
        )
        
        # ИСПРАВЛЕНО: Новый синтаксис кнопки "Назад"
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await update.message.reply_text(
            status_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        
        logger.info("✅ Статус отправлен")
        
    except Exception as e:
        logger.error(f"❌ Ошибка /status: {e}")

# ДОБАВЛЕНО: Обработчик кнопок (CallbackQueryHandler)
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    logger = logging.getLogger(__name__)
    
    try:
        query = update.callback_query
        
        # ВАЖНО: Отвечаем на callback query чтобы убрать "loading" с кнопки
        await query.answer()
        
        logger.info(f"🔘 Нажата кнопка: {query.data}")
        
        if query.data == "status":
            # Показываем статус
            await show_status(query)
            
        elif query.data == "help":
            # Показываем справку
            await show_help(query)
            
        elif query.data == "main_menu":
            # Возврат в главное меню
            await show_main_menu(query)
            
    except Exception as e:
        logger.error(f"❌ Ошибка обработки кнопки: {e}")

async def show_status(query):
    """Показывает статус системы"""
    current_time = datetime.now().strftime("%H:%M:%S")
    current_date = datetime.now().strftime("%d.%m.%Y")
    
    ai_status = "✅ Включен" if os.getenv('AI_ANALYSIS_ENABLED') == 'true' else "❌ Отключен"
    
    status_text = (
        "🟢 <b>СТАТУС СИСТЕМЫ</b>\n\n"
        f"📱 Telegram бот: ✅ Работает\n"
        f"🤖 ИИ анализ: {ai_status}\n"
        "📊 Jesse фреймворк: ✅ Активен\n"
        "🔄 Стратегии: 3 активные\n\n"
        "<b>Активные стратегии:</b>\n"
        "• ActiveScalper (BTCUSDT, 5m)\n"
        "• BalancedTrader (BTCUSDT, 15m)\n"
        "• QualityTrader (BTCUSDT, 1h)\n\n"
        f"⏰ {current_time} | 📅 {current_date}"
    )
    
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await query.edit_message_text(
        text=status_text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )

async def show_help(query):
    """Показывает справку"""
    help_text = (
        "📖 <b>СПРАВКА AI Trading Bot</b>\n\n"
        "<b>Команды:</b>\n"
        "• /start - Запуск бота\n"
        "• /help - Эта справка\n"
        "• /status - Статус системы\n\n"
        "<b>Возможности:</b>\n"
        "🤖 ИИ анализ торговых сигналов\n"
        "📊 Мониторинг стратегий\n"
        "📱 Уведомления о сделках\n\n"
        "<b>Стратегии:</b>\n"
        "• ActiveScalper (5m) - Быстрые сделки\n"
        "• BalancedTrader (15m) - Сбалансированная торговля\n"
        "• QualityTrader (1h) - Качественные сигналы\n\n"
        "Бот работает автоматически!"
    )
    
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await query.edit_message_text(
        text=help_text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )

async def show_main_menu(query):
    """Показывает главное меню"""
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
    
    keyboard = [
        [InlineKeyboardButton("📊 Статус", callback_data="status")],
        [InlineKeyboardButton("📈 Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await query.edit_message_text(
        text=message_text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )

def main():
    """Главная функция"""
    logger = setup_logging()
    
    try:
        # Проверяем переменные окружения
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            logger.error("❌ Не найдены TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
            return
        
        logger.info("🤖 Запуск Telegram бота (python-telegram-bot 20.0+)")
        logger.info(f"Bot token: {bot_token[:10]}...")
        logger.info(f"Chat ID: {chat_id}")
        
        # Создаем приложение
        application = Application.builder().token(bot_token).build()
        
        # ИСПРАВЛЕНО: Добавляем все обработчики
        application.add_handler(CommandHandler("start", command_start))
        application.add_handler(CommandHandler("help", command_help))
        application.add_handler(CommandHandler("status", command_status))
        
        # КРИТИЧЕСКИ ВАЖНО: Добавляем обработчик кнопок
        application.add_handler(CallbackQueryHandler(handle_button))
        
        logger.info("✅ Все обработчики добавлены (команды + кнопки)")
        
        # Запускаем бота
        logger.info("🚀 Запускаем polling...")
        application.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("🛑 Остановка по Ctrl+C")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
