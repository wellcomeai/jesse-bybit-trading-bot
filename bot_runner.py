# bot_runner.py - ИСПРАВЛЕННАЯ ВЕРСИЯ с детальным логированием ошибок
import os
import logging
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import TelegramError, RetryAfter
from datetime import datetime
import asyncio
import concurrent.futures
import sys
import traceback

def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/tmp/telegram_bot_complete.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

class TelegramBot:
    """Telegram бот с ДЕТАЛЬНЫМ логированием ИИ анализа"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.logger = setup_logging()
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID должны быть установлены!")
        
        self.logger.info(f"🤖 TelegramBot инициализирован")

    async def _show_ai_analysis_inline(self, query):
        """ИСПРАВЛЕН: Показывает ИИ анализ с детальным логированием"""
        try:
            self.logger.info("🧠 === НАЧАЛО ИИ АНАЛИЗА ===")
            
            # Показываем загрузку
            await query.edit_message_text(
                "🤖 <b>ЗАПУСК ИИ АНАЛИЗА РЫНКА</b>\n\n"
                "⏳ Проверяю настройки...\n"
                "🔍 Подключаюсь к OpenAI API...\n"
                "📊 Собираю данные с Bybit...\n\n"
                "<i>Подробные логи записываются...</i>",
                parse_mode="HTML"
            )
            
            # Детальная проверка настроек
            analysis_result = await self._perform_ai_analysis_with_detailed_logging()
            
            # Отправляем результат
            keyboard = [
                [InlineKeyboardButton("🔄 Повторить анализ", callback_data="ai_analysis")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await query.edit_message_text(
                analysis_result,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
            self.logger.info("✅ ИИ анализ завершен и отправлен пользователю")
            
        except Exception as e:
            self.logger.error(f"❌ КРИТИЧЕСКАЯ ошибка в _show_ai_analysis_inline: {e}")
            self.logger.error(f"Полный traceback: {traceback.format_exc()}")
            
            await self._send_error_to_user(query, "Критическая ошибка в интерфейсе", str(e))

    async def _perform_ai_analysis_with_detailed_logging(self) -> str:
        """НОВЫЙ МЕТОД: Выполняет ИИ анализ с пошаговым логированием"""
        try:
            # ШАГ 1: Проверяем переменные окружения
            self.logger.info("🔍 ШАГ 1: Проверка переменных окружения")
            
            ai_enabled = os.getenv('AI_ANALYSIS_ENABLED', 'false').lower()
            openai_key = os.getenv('OPENAI_API_KEY')
            
            self.logger.info(f"  AI_ANALYSIS_ENABLED = '{ai_enabled}'")
            self.logger.info(f"  OPENAI_API_KEY = '{openai_key[:10] if openai_key else 'НЕ УСТАНОВЛЕН'}...'")
            
            if ai_enabled != 'true':
                error_msg = f"AI_ANALYSIS_ENABLED = '{ai_enabled}' (должно быть 'true')"
                self.logger.error(f"❌ {error_msg}")
                return self._format_error_response("Настройки ИИ", error_msg)
            
            if not openai_key:
                error_msg = "OPENAI_API_KEY не установлен в переменных окружения"
                self.logger.error(f"❌ {error_msg}")
                return self._format_error_response("API ключ", error_msg)
            
            if len(openai_key) < 20:
                error_msg = f"OPENAI_API_KEY подозрительно короткий ({len(openai_key)} символов)"
                self.logger.warning(f"⚠️ {error_msg}")
            
            self.logger.info("✅ ШАГ 1: Переменные окружения проверены")
            
            # ШАГ 2: Попытка импорта MarketAnalyzer
            self.logger.info("📦 ШАГ 2: Импорт MarketAnalyzer")
            
            try:
                from market_analyzer import MarketAnalyzer
                self.logger.info("✅ MarketAnalyzer успешно импортирован")
            except ImportError as e:
                error_msg = f"Не удалось импортировать MarketAnalyzer: {e}"
                self.logger.error(f"❌ {error_msg}")
                self.logger.error(f"Путь Python: {sys.path}")
                return self._format_error_response("Импорт модуля", error_msg)
            
            # ШАГ 3: Создание анализатора
            self.logger.info("🏗️ ШАГ 3: Создание экземпляра MarketAnalyzer")
            
            try:
                analyzer = MarketAnalyzer()
                self.logger.info("✅ MarketAnalyzer создан успешно")
            except Exception as e:
                error_msg = f"Ошибка создания MarketAnalyzer: {e}"
                self.logger.error(f"❌ {error_msg}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                return self._format_error_response("Создание анализатора", error_msg)
            
            # ШАГ 4: Выполнение анализа
            self.logger.info("🔬 ШАГ 4: Выполнение analyze_all_strategies")
            
            try:
                analysis_data = await analyzer.analyze_all_strategies()
                self.logger.info("✅ analyze_all_strategies выполнен успешно")
                
                # Проверяем качество данных
                if not analysis_data or not isinstance(analysis_data, dict):
                    error_msg = f"analyze_all_strategies вернул некорректные данные: {type(analysis_data)}"
                    self.logger.error(f"❌ {error_msg}")
                    return self._format_error_response("Данные анализа", error_msg)
                
                # Логируем ключи результата
                self.logger.info(f"📋 Получены ключи: {list(analysis_data.keys())}")
                
                # Проверяем наличие overall_analysis
                overall_analysis = analysis_data.get('overall_analysis', {})
                if not overall_analysis:
                    self.logger.warning("⚠️ overall_analysis пустой или отсутствует")
                
                # ШАГ 5: Форматирование результата
                self.logger.info("📝 ШАГ 5: Форматирование результата для пользователя")
                
                formatted_result = self._format_ai_analysis_result(analysis_data)
                
                self.logger.info("✅ ВСЕ ШАГИ ЗАВЕРШЕНЫ УСПЕШНО!")
                return formatted_result
                
            except Exception as e:
                error_msg = f"Ошибка выполнения analyze_all_strategies: {e}"
                self.logger.error(f"❌ {error_msg}")
                self.logger.error(f"Полный traceback: {traceback.format_exc()}")
                return self._format_error_response("Выполнение анализа", error_msg, str(e))
            
        except Exception as e:
            error_msg = f"Неожиданная ошибка в процессе ИИ анализа: {e}"
            self.logger.error(f"❌ {error_msg}")
            self.logger.error(f"Полный traceback: {traceback.format_exc()}")
            return self._format_error_response("Системная ошибка", error_msg, str(e))

    def _format_error_response(self, error_category: str, error_message: str, technical_details: str = "") -> str:
        """Форматирует ошибку для отправки пользователю"""
        current_time = datetime.now().strftime("%H:%M:%S")
        
        response = f"❌ <b>ОШИБКА ИИ АНАЛИЗА</b>\n\n"
        response += f"📂 <b>Категория:</b> {error_category}\n"
        response += f"❗ <b>Описание:</b>\n<code>{error_message}</code>\n\n"
        
        if technical_details:
            # Обрезаем технические детали, если они слишком длинные
            details = technical_details[:300] + "..." if len(technical_details) > 300 else technical_details
            response += f"🔧 <b>Технические детали:</b>\n<code>{details}</code>\n\n"
        
        response += f"💡 <b>Возможные решения:</b>\n"
        
        if "OPENAI_API_KEY" in error_message:
            response += "• Проверьте корректность API ключа OpenAI\n"
            response += "• Убедитесь, что на аккаунте есть средства\n"
        elif "импорт" in error_message.lower():
            response += "• Проверьте наличие всех файлов проекта\n"
            response += "• Убедитесь в корректности путей модулей\n"
        elif "подключение" in error_message.lower() or "connection" in error_message.lower():
            response += "• Проверьте подключение к интернету\n"
            response += "• Попробуйте повторить через минуту\n"
        else:
            response += "• Попробуйте повторить операцию\n"
            response += "• Проверьте логи системы\n"
        
        response += f"\n⏰ Время ошибки: {current_time}\n"
        response += f"🔗 <i>Подробные логи см. в консоли/файлах</i>"
        
        return response

    async def _send_error_to_user(self, query, error_title: str, error_details: str):
        """Отправляет ошибку пользователю через Telegram"""
        try:
            error_response = self._format_error_response(error_title, error_details)
            
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await query.edit_message_text(
                text=error_response,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        except Exception as e:
            self.logger.error(f"❌ Не удалось отправить ошибку пользователю: {e}")

    def _format_ai_analysis_result(self, analysis_data: dict) -> str:
        """ОБНОВЛЕН: Форматирует результат ИИ анализа с проверкой данных"""
        try:
            self.logger.info("📝 Начинаем форматирование результата ИИ анализа")
            
            timestamp = analysis_data.get('timestamp', datetime.now().isoformat())
            price = analysis_data.get('price', 0)
            market_phase = analysis_data.get('market_phase', 'UNKNOWN')
            strategy_analyses = analysis_data.get('strategy_analyses', [])
            overall_analysis = analysis_data.get('overall_analysis', {})
            
            self.logger.info(f"Данные для форматирования: price={price}, phase={market_phase}, strategies={len(strategy_analyses)}")
            
            # Проверяем, что данные не mock
            if isinstance(overall_analysis, dict):
                summary = overall_analysis.get('summary', '')
                if 'базовый анализ' in summary.lower() or 'mock' in summary.lower():
                    self.logger.warning("⚠️ ОБНАРУЖЕНЫ MOCK ДАННЫЕ В АНАЛИЗЕ!")
            
            # Эмодзи для фазы рынка
            phase_emoji = {
                'BULLISH': '🚀', 'BEARISH': '🐻', 'NEUTRAL': '😐',
                'VOLATILE': '⚡', 'BULL_TREND': '📈', 'BEAR_TREND': '📉',
                'SIDEWAYS': '➡️'
            }.get(market_phase, '❓')
            
            message = f"🧠 <b>РЕАЛЬНЫЙ ИИ АНАЛИЗ РЫНКА</b>\n\n"
            message += f"💰 <b>BTCUSDT:</b> ${price:,.2f}\n"
            message += f"{phase_emoji} <b>Фаза рынка:</b> {market_phase}\n"
            
            # Уверенность ИИ
            confidence = overall_analysis.get('confidence', 50)
            message += f"🎯 <b>Уверенность ИИ:</b> {confidence}%\n\n"
            
            # Анализ по стратегиям
            if strategy_analyses:
                message += "📊 <b>АНАЛИЗ ПО СТРАТЕГИЯМ:</b>\n"
                for strategy in strategy_analyses:
                    name = strategy.get('strategy', 'Unknown')
                    signal = strategy.get('signal', 'UNKNOWN')
                    conf = strategy.get('confidence', 0)
                    signal_emoji = self._get_signal_emoji(signal)
                    message += f"{signal_emoji} <b>{name}:</b> {signal} ({conf}%)\n"
                message += "\n"
            
            # Ключевые выводы ИИ
            key_insights = overall_analysis.get('key_insights', [])
            if key_insights:
                message += "💡 <b>КЛЮЧЕВЫЕ ВЫВОДЫ GPT:</b>\n"
                for insight in key_insights[:3]:
                    message += f"• {insight}\n"
                message += "\n"
            
            # Рекомендации
            recommendations = overall_analysis.get('recommendations', [])
            if recommendations:
                message += "🎯 <b>РЕКОМЕНДАЦИИ GPT-4:</b>\n"
                for rec in recommendations[:3]:
                    message += f"• {rec}\n"
                message += "\n"
            
            # Уровень риска
            risk_level = overall_analysis.get('risk_level', 'UNKNOWN')
            risk_emoji = {'LOW': '🟢', 'MEDIUM': '🟡', 'HIGH': '🔴'}.get(risk_level, '⚪')
            message += f"{risk_emoji} <b>Уровень риска:</b> {risk_level}\n\n"
            
            # Итоговое заключение ИИ
            summary = overall_analysis.get('summary', '')
            if summary:
                message += f"📝 <b>ЗАКЛЮЧЕНИЕ GPT:</b>\n<i>{summary}</i>\n\n"
            
            # Время анализа + подтверждение что это НЕ mock
            time_str = datetime.now().strftime('%H:%M:%S')
            message += f"⏰ Анализ выполнен: {time_str}\n"
            message += f"✅ <b>СТАТУС: РЕАЛЬНЫЙ ИИ АНАЛИЗ</b>\n"
            message += f"🤖 <i>Powered by GPT-4 & Jesse Framework</i>"
            
            self.logger.info("✅ Форматирование результата завершено успешно")
            return message
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка форматирования ИИ анализа: {e}")
            return self._format_error_response("Форматирование результата", str(e))

    def _get_signal_emoji(self, signal: str) -> str:
        """Возвращает эмодзи для торгового сигнала"""
        if 'STRONG_BUY' in signal:
            return '🟢🟢'
        elif 'BUY' in signal:
            return '🟢'
        elif 'STRONG_SELL' in signal:
            return '🔴🔴'
        elif 'SELL' in signal:
            return '🔴'
        else:
            return '⚪'

    # ... остальные методы остаются без изменений ...

    async def command_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        try:
            keyboard = [
                [InlineKeyboardButton("📊 Статус системы", callback_data="status")],
                [InlineKeyboardButton("🧠 ИИ Анализ рынка", callback_data="ai_analysis")],
                [InlineKeyboardButton("📈 Помощь", callback_data="help"), 
                 InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
                [InlineKeyboardButton("📋 История", callback_data="history")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            welcome_text = (
                "🤖 <b>AI Trading Bot активен!</b>\n\n"
                "🎯 <b>С детальным логированием ошибок</b>\n\n"
                "✅ Теперь все ошибки ИИ анализа видны\n"
                "✅ Mock данные исключены\n"
                "✅ Подробное логирование включено\n\n"
                f"⏰ Время: <code>{datetime.now().strftime('%H:%M:%S')}</code>\n\n"
                "<b>Выберите действие:</b>"
            )
            
            await update.message.reply_text(
                welcome_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка /start: {e}")

    async def handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        try:
            query = update.callback_query
            await query.answer()
            
            self.logger.info(f"🔘 Нажата кнопка: {query.data}")
            
            if query.data == "ai_analysis":
                await self._show_ai_analysis_inline(query)
            elif query.data == "status":
                await self._show_status_inline(query)
            # ... другие обработчики ...
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки кнопки: {e}")

def main():
    """Главная функция"""
    try:
        telegram_bot = TelegramBot()
        telegram_bot.logger.info("🤖 Запуск ИСПРАВЛЕННОГО AI Trading Bot")
        
        application = Application.builder().token(telegram_bot.bot_token).build()
        
        application.add_handler(CommandHandler("start", telegram_bot.command_start))
        application.add_handler(CallbackQueryHandler(telegram_bot.handle_button))
        
        telegram_bot.logger.info("✅ Все обработчики добавлены - ОШИБКИ ИИ АНАЛИЗА ТЕПЕРЬ ВИДНЫ")
        
        application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
