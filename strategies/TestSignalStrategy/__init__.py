# strategies/TestSignalStrategy/__init__.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
from jesse.strategies import Strategy
import jesse.indicators as ta
import logging


class TestSignalStrategy(Strategy):
    """
    ИСПРАВЛЕННАЯ тестовая стратегия для проверки сигналов
    
    Изменения:
    - Увеличен min_price_change до 0.05%
    - Увеличен размер позиции до 0.01 BTC
    - Упрощена логика сигналов
    - Убраны конфликтующие методы из EnhancedStrategy
    """
    
    def __init__(self):
        super().__init__()
        
        # === ИСПРАВЛЕННЫЕ НАСТРОЙКИ ===
        self.min_price_change = 0.05        # Увеличено с 0.01% до 0.05%
        self.signal_counter = 0
        self.last_signal_price = None
        
        # === УВЕЛИЧЕННЫЙ РАЗМЕР ПОЗИЦИИ ===
        self.position_size = 0.01           # Увеличено с 0.001 до 0.01 BTC
        
        # === КОНТРОЛЬ ЧАСТОТЫ ===
        self.max_signals_per_hour = 10      # Уменьшено для стабильности
        self.min_gap_bars = 5               # Увеличен промежуток до 5 минут
        self.last_signal_bar = None
        
        logging.info(f"🧪 TEST STRATEGY INITIALIZED (FIXED VERSION)")
        logging.info(f"⏱️  Timeframe: 1 minute")
        logging.info(f"🎯 Min price change: {self.min_price_change}%")
        logging.info(f"💰 Position size: {self.position_size} BTC")

    def _has_sufficient_price_change(self):
        """Проверяет достаточное изменение цены для сигнала"""
        if self.index < 2:  # Нужно минимум 2 свечи
            return False
        
        current_price = self.close
        previous_price = self.candles[-2, 4]  # Цена закрытия предыдущей свечи
        
        if previous_price <= 0:  # Защита от деления на ноль
            return False
        
        price_change_percent = abs(current_price - previous_price) / previous_price * 100
        
        return price_change_percent >= self.min_price_change
    
    def _can_generate_signal(self):
        """Базовые проверки для генерации сигнала"""
        # Минимум данных
        if self.index < 5:  # Увеличено до 5 свечей
            return False
        
        # Уже есть позиция - не генерируем новые сигналы
        if self.position.is_open:
            return False
        
        # Минимальный промежуток между сигналами
        if (self.last_signal_bar is not None and 
            (self.index - self.last_signal_bar) < self.min_gap_bars):
            return False
        
        # Контроль частоты сигналов
        if self.signal_counter >= self.max_signals_per_hour:
            if self.index % 60 == 0:  # Сбрасываем счетчик каждый час
                self.signal_counter = 0
                logging.info("🔄 Счетчик сигналов сброшен")
            else:
                return False
        
        return True
    
    def _get_signal_direction(self):
        """Определяет направление сигнала на основе движения цены"""
        current_price = self.close
        previous_price = self.candles[-2, 4]
        
        # Простая логика: покупаем при росте, продаем при падении
        if current_price > previous_price:
            return "LONG"
        else:
            return "SHORT"

    def should_long(self) -> bool:
        """Условия для LONG сигнала"""
        if not self._can_generate_signal():
            return False
        
        if not self._has_sufficient_price_change():
            return False
        
        signal_direction = self._get_signal_direction()
        
        if signal_direction == "LONG":
            current_price = self.close
            previous_price = self.candles[-2, 4]
            price_change = (current_price - previous_price) / previous_price * 100
            
            self.signal_counter += 1
            self.last_signal_price = current_price
            self.last_signal_bar = self.index
            
            logging.info(f"🟢 LONG SIGNAL #{self.signal_counter}")
            logging.info(f"   Price: ${previous_price:.2f} → ${current_price:.2f} (+{price_change:.3f}%)")
            logging.info(f"   Bar: {self.index}")
            
            return True
        
        return False
    
    def should_short(self) -> bool:
        """Условия для SHORT сигнала"""
        if not self._can_generate_signal():
            return False
        
        if not self._has_sufficient_price_change():
            return False
        
        signal_direction = self._get_signal_direction()
        
        if signal_direction == "SHORT":
            current_price = self.close
            previous_price = self.candles[-2, 4]
            price_change = (current_price - previous_price) / previous_price * 100
            
            self.signal_counter += 1
            self.last_signal_price = current_price
            self.last_signal_bar = self.index
            
            logging.info(f"🔴 SHORT SIGNAL #{self.signal_counter}")
            logging.info(f"   Price: ${previous_price:.2f} → ${current_price:.2f} ({price_change:.3f}%)")
            logging.info(f"   Bar: {self.index}")
            
            return True
        
        return False
    
    def should_cancel_entry(self) -> bool:
        """Отменяем ли вход (пока не используется)"""
        return False
    
    def go_long(self):
        """Открываем LONG позицию с исправленными параметрами"""
        entry_price = self.close
        
        # Исправленные уровни стоп-лосса и тейк-профита
        stop_loss_percent = 0.5    # 0.5% стоп-лосс
        take_profit_percent = 1.0   # 1.0% тейк-профит
        
        stop_loss_price = entry_price * (1 - stop_loss_percent / 100)
        take_profit_price = entry_price * (1 + take_profit_percent / 100)
        
        # Размещаем ордера - ИСПРАВЛЕНО: используем self.buy напрямую
        self.buy = self.position_size, entry_price
        self.stop_loss = self.position_size, stop_loss_price
        self.take_profit = self.position_size, take_profit_price
        
        logging.info(f"🚀 LONG POSITION OPENED")
        logging.info(f"   Size: {self.position_size} BTC @ ${entry_price:.2f}")
        logging.info(f"   SL: ${stop_loss_price:.2f} (-{stop_loss_percent}%)")
        logging.info(f"   TP: ${take_profit_price:.2f} (+{take_profit_percent}%)")
    
    def go_short(self):
        """Открываем SHORT позицию с исправленными параметрами"""
        entry_price = self.close
        
        # Исправленные уровни для SHORT
        stop_loss_percent = 0.5    # 0.5% стоп-лосс
        take_profit_percent = 1.0   # 1.0% тейк-профит
        
        stop_loss_price = entry_price * (1 + stop_loss_percent / 100)
        take_profit_price = entry_price * (1 - take_profit_percent / 100)
        
        # Размещаем ордера - ИСПРАВЛЕНО: используем self.sell напрямую
        self.sell = self.position_size, entry_price
        self.stop_loss = self.position_size, stop_loss_price
        self.take_profit = self.position_size, take_profit_price
        
        logging.info(f"🔻 SHORT POSITION OPENED")
        logging.info(f"   Size: {self.position_size} BTC @ ${entry_price:.2f}")
        logging.info(f"   SL: ${stop_loss_price:.2f} (+{stop_loss_percent}%)")
        logging.info(f"   TP: ${take_profit_price:.2f} (-{take_profit_percent}%)")
    
    def update_position(self):
        """Обновление позиции (для будущих улучшений)"""
        pass
    
    def on_close_position(self, order):
        """Обработка закрытия позиции"""
        if hasattr(self, 'position') and self.position:
            pnl = self.position.pnl
            logging.info(f"🏁 POSITION CLOSED")
            logging.info(f"   Exit price: ${order.price:.2f}")
            logging.info(f"   P&L: ${pnl:.4f}")
    
    def before(self):
        """Мониторинг каждые 15 минут"""
        if self.index % 15 == 0 and self.index > 0:
            current_price = self.close
            
            logging.info(f"📊 MONITOR (Bar {self.index}):")
            logging.info(f"   Current price: ${current_price:.2f}")
            logging.info(f"   Signals generated: {self.signal_counter}")
            logging.info(f"   Position: {'🟢 OPEN' if self.position.is_open else '⚪ CLOSED'}")
            
            if self.position.is_open:
                position_age = self.index - self.last_signal_bar if self.last_signal_bar else 0
                logging.info(f"   Position age: {position_age} minutes | P&L: ${self.position.pnl:.4f}")
