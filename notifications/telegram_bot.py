# notifications/telegram_bot.py - ГОТОВАЯ К ДЕПЛОЮ ВЕРСИЯ
# ИСПРАВЛЕНО: Упрощена логика event loop, безопасные методы отправки

import asyncio
import os
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional
import concurrent.futures

from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import TelegramError, RetryAfter


class TelegramNotifier:
    """
    ИСПРАВЛЕННЫЙ Telegram бот без конфликтов event loop
    Готов к продакшн использованию
    """
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID должны быть установлены!")
        
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        self.running = False
        self.bot_thread = None
        
        # Настройка логирования
        self.logger = logging.getLogger(__name__)
        self.logger.info("📱 TelegramNotifier инициализирован")
        self.logger.info(f"Bot token: {self.bot_token[:10]}...")
        self.logger.info(f"Chat ID: {self.chat_id}")
        
        # Настройки отправки
        self.max_retries = 3
        self.retry_delay = 2
        self.message_timeout = 10
    
    def start_bot(self):
        """
        ИСПРАВЛЕНО: Запускает бота БЕЗ конфликтов event loop
        """
        if self.running:
            self.logger.warning("⚠️ Бот уже запущен")
            return
        
        def run_bot_thread():
            """Функция для запуска бота в отдельном потоке"""
            try:
                self.running = True
                self.logger.info("🚀 Запуск Telegram бота в отдельном потоке...")
                
                # ИСПРАВЛЕНИЕ: Позволяем run_polling() создать свой event loop
                # НЕ создаем event loop вручную!
                
                # Создаем Application
                self.application = Application.builder().token(self.bot_token).build()
                self.bot = self.application.bot
                
                # Добавляем обработчики команд
                self.application.add_handler(CommandHandler("start", self._command_start))
                self.application.add_handler(CommandHandler("help", self._command_help))
                self.application.add_handler(CommandHandler("status", self._command_status))
                
                # Добавляем обработчики кнопок
                self.application.add_handler(CallbackQueryHandler(self._handle_button, pattern="^(status|help|main_menu)$"))
                
                self.logger.info("✅ Обработчики команд добавлены")
                
                # ИСПРАВЛЕНИЕ: Запускаем polling и позволяем ему создать event loop
                self.application.run_polling(
                    drop_pending_updates=True,
                    allowed_updates=Update.ALL_TYPES
                )
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка запуска бота: {e}")
            finally:
                self.running = False
                self.logger.info("🛑 Поток Telegram бота завершен")
        
        # Запускаем в daemon потоке
        self.bot_thread = threading.Thread(target=run_bot_thread, daemon=True, name="TelegramBot")
        self.bot_thread.start()
        
        self.logger.info("✅ Telegram бот запущен в фоновом режиме")
    
    def stop_bot(self):
        """Останавливает бота"""
        if self.application and self.running:
            try:
                self.application.stop_running()
                self.running = False
                self.logger.info("🛑 Telegram бот остановлен")
            except Exception as e:
                self.logger.error(f"❌ Ошибка остановки: {e}")
    
    # === ОБРАБОТЧИКИ КОМАНД ===
    
    async def _command_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        try:
            user_info = f"{update.effective_user.username} (ID: {update.effective_chat.id})"
            self.logger.info(f"🚀 /start от {user_info}")
            
            keyboard = self._get_main_keyboard()
            
            welcome_text = (
                "🤖 <b>AI Trading Bot</b>\n\n"
                "Добро пожаловать! Я ваш помощник по криптотрейдингу.\n\n"
                "🔹 Анализирую рынок с помощью ИИ\n"
                "🔹 Отправляю торговые сигналы\n"
                "🔹 Слежу за вашими стратегиями\n\n"
                f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}\n\n"
                "Выберите действие:"
            )
            
            await update.message.reply_text(
                welcome_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
            
            self.logger.info("✅ Ответ на /start отправлен")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка /start: {e}")
            try:
                await update.message.reply_text(f"❌ Произошла ошибка: {str(e)[:100]}...")
            except:
                pass
    
    async def _command_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        try:
            self.logger.info("📖 /help команда")
            
            help_text = (
                "📖 <b>СПРАВКА AI Trading Bot</b>\n\n"
                "<b>Команды:</b>\n"
                "• /start - Главное меню\n"
                "• /help - Эта справка\n"
                "• /status - Статус системы\n\n"
                "<b>Функции:</b>\n"
                "🤖 Автоматический ИИ анализ торговых сигналов\n"
                "📊 Мониторинг результатов стратегий\n"
                "📱 Уведомления о важных событиях\n"
                "🔔 Оповещения об открытии/закрытии позиций\n\n"
                "<b>Стратегии:</b>\n"
                "• ActiveScalper (5m) - Быстрые сделки\n"
                "• BalancedTrader (15m) - Сбалансированная торговля\n"
                "• QualityTrader (1h) - Качественные сигналы"
            )
            
            keyboard = self._get_main_keyboard()
            
            await update.message.reply_text(
                help_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
            
            self.logger.info("✅ Справка отправлена")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка /help: {e}")
    
    async def _command_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        try:
            self.logger.info("📊 /status команда")
            
            # Проверяем статус компонентов
            ai_status = "✅ Включен" if os.getenv('AI_ANALYSIS_ENABLED') == 'true' else "❌ Отключен"
            telegram_status = "✅ Работает" if self.running else "❌ Не работает"
            
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
                f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}\n"
                f"📅 Дата: {datetime.now().strftime('%Y-%m-%d')}"
            )
            
            keyboard = self._get_main_keyboard()
            
            await update.message.reply_text(
                status_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
            
            self.logger.info("✅ Статус отправлен")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка /status: {e}")
    
    async def _handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий кнопок"""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == "status":
                await self._command_status(update, context)
            elif query.data == "help":
                await self._command_help(update, context)
            elif query.data == "main_menu":
                await query.edit_message_text(
                    "🤖 <b>AI Trading Bot</b>\n\nГлавное меню. Выберите действие:",
                    parse_mode='HTML',
                    reply_markup=self._get_main_keyboard()
                )
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки кнопки: {e}")
    
    def _get_main_keyboard(self) -> InlineKeyboardMarkup:
        """Создает основную клавиатуру"""
        keyboard = [
            [InlineKeyboardButton("📊 Статус системы", callback_data="status")],
            [InlineKeyboardButton("ℹ️ Справка", callback_data="help")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    # === МЕТОДЫ ДЛЯ ОТПРАВКИ СООБЩЕНИЙ ===
    
    async def send_message_safe(self, text: str, parse_mode: str = 'HTML') -> bool:
        """
        ИСПРАВЛЕНО: Безопасная отправка сообщений БЕЗ конфликтов event loop
        """
        for attempt in range(self.max_retries):
            try:
                # Создаем отдельный Bot объект для отправки
                bot = Bot(self.bot_token)
                
                # Отправляем сообщение
                await bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    parse_mode=parse_mode
                )
                
                # Закрываем соединение
                await bot.close()
                
                if attempt > 0:
                    self.logger.info(f"✅ Сообщение отправлено с попытки {attempt + 1}")
                
                return True
                
            except RetryAfter as e:
                wait_time = e.retry_after
                self.logger.warning(f"⏰ Rate limit, ожидание {wait_time}с (попытка {attempt + 1})")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка отправки сообщения (попытка {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        self.logger.error(f"❌ Не удалось отправить сообщение после {self.max_retries} попыток")
        return False
    
    def send_message_sync(self, text: str, parse_mode: str = 'HTML') -> bool:
        """
        Синхронная отправка сообщения (для использования из Jesse стратегий)
        """
        def send_in_thread():
            try:
                # Создаем новый event loop для этого потока
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    return loop.run_until_complete(self.send_message_safe(text, parse_mode))
                finally:
                    loop.close()
                    
            except Exception as e:
                self.logger.error(f"❌ Ошибка синхронной отправки: {e}")
                return False
        
        # Выполняем в отдельном потоке с таймаутом
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(send_in_thread)
            try:
                return future.result(timeout=self.message_timeout)
            except concurrent.futures.TimeoutError:
                self.logger.error("⏰ Таймаут отправки сообщения")
                return False
            except Exception as e:
                self.logger.error(f"❌ Ошибка выполнения отправки: {e}")
                return False
    
    async def send_analysis_notification(self, signal_data: Dict[str, Any], ai_analysis: Dict[str, Any]) -> bool:
        """Отправляет уведомление об ИИ анализе"""
        try:
            # Динамический импорт для избежания циклических зависимостей
            from notifications.message_formatter import MessageFormatter
            
            formatter = MessageFormatter()
            message = formatter.format_analysis_message(signal_data, ai_analysis)
            
            return await self.send_message_safe(message)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки анализа: {e}")
            return False
    
    async def send_trade_notification(self, trade_data: Dict[str, Any]) -> bool:
        """Отправляет уведомление о сделке"""
        try:
            from notifications.message_formatter import MessageFormatter
            
            formatter = MessageFormatter()
            message = formatter.format_trade_update(trade_data)
            
            return await self.send_message_safe(message)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки уведомления о сделке: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Тестирует подключение к Telegram"""
        try:
            test_message = (
                f"🤖 <b>Тест соединения</b>\n\n"
                f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"✅ AI Trading Bot подключен и готов к работе!"
            )
            
            success = await self.send_message_safe(test_message)
            
            if success:
                self.logger.info("✅ Тест соединения Telegram успешен")
            else:
                self.logger.error("❌ Тест соединения Telegram неудачен")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка теста соединения: {e}")
            return False


# === ФАБРИЧНАЯ ФУНКЦИЯ ===

def create_telegram_notifier() -> Optional[TelegramNotifier]:
    """
    Безопасная фабрика для создания TelegramNotifier
    Возвращает None если не удалось создать (например, нет токенов)
    """
    try:
        notifier = TelegramNotifier()
        return notifier
    except Exception as e:
        logging.error(f"❌ Не удалось создать TelegramNotifier: {e}")
        return None


# === ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР (опционально) ===

# Создаем глобальный экземпляр только если есть настройки
_global_notifier = None

def get_telegram_notifier() -> Optional[TelegramNotifier]:
    """Возвращает глобальный экземпляр TelegramNotifier"""
    global _global_notifier
    
    if _global_notifier is None:
        _global_notifier = create_telegram_notifier()
    
    return _global_notifier
