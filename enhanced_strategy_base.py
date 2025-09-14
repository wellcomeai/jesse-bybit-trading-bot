# enhanced_strategy_base.py - ИСПРАВЛЕННАЯ ВЕРСИЯ без конфликтов с Jesse
from jesse.strategies import Strategy
import threading
import time
import os
import logging
from typing import Dict, Any, Optional


class EnhancedStrategy(Strategy):
    """
    ИСПРАВЛЕННЫЙ расширенный базовый класс стратегии с ИИ анализом
    
    КЛЮЧЕВЫЕ ИСПРАВЛЕНИЯ:
    - Убраны переопределения go_long() и go_short() 
    - ИИ анализ запускается после размещения ордеров
    - Нет конфликтов с базовой логикой Jesse
    """
    
    def __init__(self):
        super().__init__()
        
        # Проверяем доступность компонентов
        self.enable_ai_analysis = self._check_ai_enabled()
        self.enable_notifications = self._check_telegram_enabled()
        
        # Кэш последних анализов
        self.last_analysis_time = {}
        self.min_analysis_gap = 300  # 5 минут между анализами
        
        # Логирование состояния
        if self.enable_ai_analysis:
            self.log("🤖 ИИ анализ ВКЛЮЧЕН (исправленная версия)")
        else:
            self.log("⚠️ ИИ анализ ОТКЛЮЧЕН")
            
        if self.enable_notifications:
            self.log("📱 Telegram уведомления ВКЛЮЧЕНЫ")
        else:
            self.log("⚠️ Telegram уведомления ОТКЛЮЧЕНЫ")
    
    def _check_ai_enabled(self) -> bool:
        """Проверяет доступность ИИ анализа"""
        try:
            ai_enabled = os.getenv('AI_ANALYSIS_ENABLED', 'false').lower() in ('true', '1', 'yes')
            openai_key = bool(os.getenv('OPENAI_API_KEY'))
            return ai_enabled and openai_key
        except Exception:
            return False
    
    def _check_telegram_enabled(self) -> bool:
        """Проверяет доступность Telegram"""
        try:
            telegram_enabled = os.getenv('TELEGRAM_ENABLED', 'false').lower() in ('true', '1', 'yes')
            bot_token = bool(os.getenv('TELEGRAM_BOT_TOKEN'))
            chat_id = bool(os.getenv('TELEGRAM_CHAT_ID'))
            return telegram_enabled and bot_token and chat_id
        except Exception:
            return False
    
    # === ИСПРАВЛЕНИЕ: НЕ переопределяем go_long() и go_short() ===
    # Вместо этого используем колбэки после размещения ордеров
    
    def on_open_position(self, order):
        """
        ИСПРАВЛЕНО: Вызывается AFTER позиция открыта
        Здесь запускаем ИИ анализ БЕЗ конфликтов с Jesse
        """
        try:
            if hasattr(super(), 'on_open_position'):
                super().on_open_position(order)
            
            # Определяем тип сигнала
            signal_type = 'LONG' if self.is_long else 'SHORT' if self.is_short else 'UNKNOWN'
            
            self.log(f"📈 Позиция открыта: {signal_type} на {self.symbol} по цене {order.price}")
            
            # Запускаем ИИ анализ ПОСЛЕ открытия позиции
            if self.enable_ai_analysis:
                self._trigger_ai_analysis_async(
                    signal_type=signal_type,
                    reason=f"Position opened at {order.price}",
                    additional_data={
                        'entry_price': float(order.price),
                        'position_size': float(order.qty)
                    }
                )
            
        except Exception as e:
            self.log(f"❌ Ошибка в on_open_position: {e}")
    
    def on_close_position(self, order):
        """
        ИСПРАВЛЕНО: Анализируем результат сделки
        """
        try:
            if hasattr(super(), 'on_close_position'):
                super().on_close_position(order)
            
            pnl = float(self.position.pnl) if hasattr(self, 'position') and self.position else 0
            self.log(f"🏁 Позиция закрыта на {self.symbol}. P&L: ${pnl:.2f}")
            
            # Анализируем результат сделки
            if self.enable_ai_analysis:
                self._trigger_ai_analysis_async(
                    signal_type='EXIT',
                    reason='Position closed',
                    additional_data={
                        'exit_price': float(order.price),
                        'pnl': pnl,
                        'exit_reason': 'TP_SL_or_Manual'
                    }
                )
                
        except Exception as e:
            self.log(f"❌ Ошибка в on_close_position: {e}")
    
    def _trigger_ai_analysis_async(self, signal_type: str, reason: str, additional_data: Dict = None):
        """
        ИСПРАВЛЕНО: Запускает ИИ анализ в отдельном потоке БЕЗ конфликта с Jesse
        """
        if not self.enable_ai_analysis:
            return
        
        strategy_name = self.__class__.__name__
        current_time = time.time()
        
        # Проверяем частоту анализов
        if (strategy_name in self.last_analysis_time and 
            current_time - self.last_analysis_time[strategy_name] < self.min_analysis_gap):
            self.log(f"⏰ Пропускаем ИИ анализ - слишком рано ({self.min_analysis_gap}с)")
            return
        
        # Собираем данные для анализа
        try:
            signal_data = self._collect_signal_data(signal_type, reason, additional_data)
        except Exception as e:
            self.log(f"❌ Ошибка сбора данных сигнала: {e}")
            return
        
        # Запускаем анализ в отдельном daemon потоке
        def run_analysis_in_thread():
            """Функция для выполнения ИИ анализа в отдельном потоке"""
            try:
                import asyncio
                
                # Создаем НОВЫЙ event loop только для этого потока
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def perform_analysis():
                    try:
                        # Динамический импорт для избежания ошибок
                        from ai_analysis.openai_analyzer import OpenAIAnalyzer
                        from ai_analysis.market_context import MarketContextCollector
                        
                        analyzer = OpenAIAnalyzer()
                        context_collector = MarketContextCollector()
                        
                        self.log(f"🤖 Запускаем ИИ анализ: {signal_type}")
                        
                        # Собираем рыночный контекст
                        market_data = await context_collector.collect_context(
                            symbol=self.symbol,
                            timeframe=self.timeframe,
                            candles_data=self.candles
                        )
                        
                        # Выполняем ИИ анализ
                        ai_analysis = await analyzer.analyze_signal(signal_data, market_data)
                        
                        if ai_analysis:
                            recommendation = ai_analysis.get('recommendation', 'UNKNOWN')
                            confidence = ai_analysis.get('confidence', 0)
                            self.log(f"✅ ИИ анализ: {recommendation} ({confidence}%)")
                            
                            # Отправляем уведомление если включено
                            if self.enable_notifications:
                                await self._send_notification_async(signal_data, ai_analysis)
                        else:
                            self.log("⚠️ ИИ анализ не дал результата")
                        
                        # Обновляем время последнего анализа
                        self.last_analysis_time[strategy_name] = current_time
                        
                    except Exception as e:
                        self.log(f"❌ Ошибка ИИ анализа: {e}")
                
                # Выполняем анализ в этом event loop
                loop.run_until_complete(perform_analysis())
                
            except Exception as e:
                self.log(f"❌ Ошибка потока ИИ анализа: {e}")
            finally:
                try:
                    loop.close()
                except Exception:
                    pass
        
        # Запускаем в daemon потоке
        analysis_thread = threading.Thread(
            target=run_analysis_in_thread, 
            daemon=True,
            name=f"AI_Analysis_{strategy_name}_{int(current_time)}"
        )
        analysis_thread.start()
        
        self.log(f"🚀 ИИ анализ запущен в потоке: {analysis_thread.name}")
    
    async def _send_notification_async(self, signal_data: Dict, ai_analysis: Dict):
        """Отправляет уведомление через Telegram"""
        try:
            from notifications.telegram_bot import TelegramNotifier
            from notifications.message_formatter import MessageFormatter
            
            notifier = TelegramNotifier()
            formatter = MessageFormatter()
            
            message = formatter.format_analysis_message(signal_data, ai_analysis)
            success = await notifier.send_message_safe(message)
            
            if success:
                self.log("📱 Уведомление отправлено в Telegram")
            else:
                self.log("❌ Не удалось отправить уведомление")
                
        except Exception as e:
            self.log(f"❌ Ошибка отправки уведомления: {e}")
    
    def _collect_signal_data(self, signal_type: str, reason: str, additional_data: Dict = None) -> Dict[str, Any]:
        """Собирает данные о торговом сигнале"""
        try:
            return {
                'strategy': self.__class__.__name__,
                'signal_type': signal_type,
                'reason': reason,
                'price': float(self.close),
                'timestamp': int(time.time()),
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'exchange': self.exchange,
                
                'candles_data': {
                    'recent_candles': self._get_recent_candles_data(20),
                    'current_volume': float(self.candles[-1, 5]) if len(self.candles) > 0 else 0,
                },
                
                'indicators': self._get_current_indicators(),
                'additional_data': additional_data or {}
            }
        except Exception as e:
            self.log(f"❌ Ошибка сбора данных сигнала: {e}")
            return {
                'strategy': self.__class__.__name__,
                'signal_type': signal_type,
                'reason': reason,
                'price': float(self.close) if hasattr(self, 'close') else 0,
                'timestamp': int(time.time()),
                'symbol': getattr(self, 'symbol', 'UNKNOWN'),
                'timeframe': getattr(self, 'timeframe', 'UNKNOWN'),
                'exchange': getattr(self, 'exchange', 'UNKNOWN'),
                'error': 'Failed to collect full data'
            }
    
    def _get_recent_candles_data(self, count: int = 20) -> list:
        """Получает данные последних свечей"""
        try:
            if not hasattr(self, 'candles') or len(self.candles) == 0:
                return []
            
            actual_count = min(count, len(self.candles))
            candles_list = []
            
            for i in range(-actual_count, 0):
                candle = self.candles[i]
                candles_list.append({
                    'timestamp': int(candle[0]) if len(candle) > 0 else 0,
                    'open': float(candle[1]) if len(candle) > 1 else 0,
                    'high': float(candle[2]) if len(candle) > 2 else 0,
                    'low': float(candle[3]) if len(candle) > 3 else 0,
                    'close': float(candle[4]) if len(candle) > 4 else 0,
                    'volume': float(candle[5]) if len(candle) > 5 else 0,
                })
            
            return candles_list
            
        except Exception as e:
            self.log(f"⚠️ Ошибка получения данных свечей: {e}")
            return []
    
    def _get_current_indicators(self) -> Dict[str, Any]:
        """Получает текущие значения индикаторов (переопределяется в стратегиях)"""
        indicators = {}
        
        try:
            # Базовые индикаторы, если доступны
            if hasattr(self, 'rsi'):
                indicators['rsi'] = float(self.rsi)
            if hasattr(self, 'ema21'):
                indicators['ema21'] = float(self.ema21)
            if hasattr(self, 'ema50'):
                indicators['ema50'] = float(self.ema50)
            if hasattr(self, 'bb_upper'):
                indicators['bb_upper'] = float(self.bb_upper)
            if hasattr(self, 'bb_lower'):
                indicators['bb_lower'] = float(self.bb_lower)
            if hasattr(self, 'atr'):
                indicators['atr'] = float(self.atr)
            
            # Текущая цена как индикатор
            if hasattr(self, 'close'):
                indicators['current_price'] = float(self.close)
                
        except Exception as e:
            self.log(f"⚠️ Ошибка получения индикаторов: {e}")
        
        return indicators
