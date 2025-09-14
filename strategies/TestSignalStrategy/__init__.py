# strategies/TestSignalStrategy/__init__.py
from enhanced_strategy_base import EnhancedStrategy
import jesse.indicators as ta


class TestSignalStrategy(EnhancedStrategy):
    """
    ТЕСТОВАЯ СТРАТЕГИЯ ДЛЯ ПРОВЕРКИ СИГНАЛОВ
    
    Цель: Генерировать сигнал каждую минуту при любом изменении цены
    Таймфрейм: 1 минута
    Логика: Если цена изменилась относительно предыдущей свечи - генерируем сигнал
    
    Используется для:
    - Проверки работы системы сигналов
    - Тестирования ИИ анализа в реальном времени
    - Проверки Telegram уведомлений
    """
    
    def __init__(self):
        super().__init__()
        
        # === ПРОСТЫЕ НАСТРОЙКИ ===
        self.min_price_change = 0.01    # Минимальное изменение цены в % (0.01% = $4 для BTC $40k)
        self.signal_counter = 0         # Счетчик сигналов
        self.last_signal_price = None   # Цена последнего сигнала
        self.alternate_direction = True # Чередуем LONG/SHORT для тестирования
        
        # === УПРАВЛЕНИЕ РИСКАМИ (минимальные для теста) ===
        self.risk_percent = 0.1         # Очень маленький риск 0.1%
        self.quick_exit_bars = 3        # Быстрый выход через 3 минуты
        
        # === КОНТРОЛЬ ЧАСТОТЫ ===
        self.max_signals_per_hour = 30  # Максимум 30 сигналов в час
        self.min_gap_bars = 2           # Минимум 2 минуты между сигналами
        self.last_signal_bar = None
        
        self.log(f"🧪 === TEST SIGNAL STRATEGY INITIALIZED ===")
        self.log(f"⏱️  Timeframe: 1 minute")
        self.log(f"🎯 Min price change: {self.min_price_change}%")
        self.log(f"🤖 AI analysis: {'✅ ENABLED' if self.enable_ai_analysis else '❌ DISABLED'}")
        self.log(f"📱 Telegram: {'✅ ENABLED' if self.enable_notifications else '❌ DISABLED'}")
        self.log(f"🔄 Ready to generate test signals every minute!")

    def _has_price_changed(self):
        """Проверяем изменилась ли цена достаточно для сигнала"""
        if self.index < 1:  # Нужна минимум 1 предыдущая свеча
            return False
        
        current_price = self.close
        previous_price = self.candles[-2, 4]  # Цена закрытия предыдущей свечи
        
        price_change_percent = abs(current_price - previous_price) / previous_price * 100
        
        return price_change_percent >= self.min_price_change
    
    def _can_generate_signal(self):
        """Базовые проверки для генерации сигнала"""
        # Минимум данных
        if self.index < 2:
            return False
        
        # Уже есть позиция - не генерируем новые сигналы
        if self.position.is_open:
            return False
        
        # Минимальный промежуток между сигналами
        if (self.last_signal_bar is not None and 
            (self.index - self.last_signal_bar) < self.min_gap_bars):
            return False
        
        # Контроль частоты (не больше 30 в час = каждые 2 минуты)
        if self.signal_counter > 0 and self.signal_counter % self.max_signals_per_hour == 0:
            self.log(f"⏸️  Пауза: достигнут лимит {self.max_signals_per_hour} сигналов в час")
            return False
        
        return True
    
    def _get_signal_direction(self):
        """Определяем направление сигнала"""
        current_price = self.close
        previous_price = self.candles[-2, 4]
        
        # Можем использовать разные логики:
        
        # 1. По направлению движения цены
        if current_price > previous_price:
            return "LONG"  # Цена растет - покупаем
        else:
            return "SHORT"  # Цена падает - продаем
        
        # 2. Или чередовать для тестирования (раскомментировать если нужно)
        # self.alternate_direction = not self.alternate_direction
        # return "LONG" if self.alternate_direction else "SHORT"

    def should_long(self) -> bool:
        """
        Условия для LONG сигнала:
        1. Базовые проверки пройдены
        2. Цена изменилась достаточно
        3. Определили что нужен LONG
        """
        if not self._can_generate_signal():
            return False
        
        if not self._has_price_changed():
            return False
        
        signal_direction = self._get_signal_direction()
        
        if signal_direction == "LONG":
            current_price = self.close
            previous_price = self.candles[-2, 4]
            price_change = (current_price - previous_price) / previous_price * 100
            
            self.signal_counter += 1
            self.last_signal_price = current_price
            
            self.log(f"🟢 TEST LONG SIGNAL #{self.signal_counter}")
            self.log(f"   Price: ${previous_price:.2f} → ${current_price:.2f} (+{price_change:.3f}%)")
            self.log(f"   Reason: Price increased, testing LONG signal")
            self.log(f"   Bar: {self.index} | Time gap: {(self.index - self.last_signal_bar) if self.last_signal_bar else 'N/A'} bars")
            
            self.entry_reason = f"TEST_PRICE_UP_{price_change:.3f}%"
            return True
        
        return False
    
    def should_short(self) -> bool:
        """
        Условия для SHORT сигнала:
        1. Базовые проверки пройдены  
        2. Цена изменилась достаточно
        3. Определили что нужен SHORT
        """
        if not self._can_generate_signal():
            return False
        
        if not self._has_price_changed():
            return False
        
        signal_direction = self._get_signal_direction()
        
        if signal_direction == "SHORT":
            current_price = self.close
            previous_price = self.candles[-2, 4]
            price_change = (current_price - previous_price) / previous_price * 100
            
            self.signal_counter += 1
            self.last_signal_price = current_price
            
            self.log(f"🔴 TEST SHORT SIGNAL #{self.signal_counter}")
            self.log(f"   Price: ${previous_price:.2f} → ${current_price:.2f} ({price_change:.3f}%)")
            self.log(f"   Reason: Price decreased, testing SHORT signal")
            self.log(f"   Bar: {self.index} | Time gap: {(self.index - self.last_signal_bar) if self.last_signal_bar else 'N/A'} bars")
            
            self.entry_reason = f"TEST_PRICE_DOWN_{price_change:.3f}%"
            return True
        
        return False
    
    def should_cancel_entry(self) -> bool:
        return False
    
    def go_long(self):
        """Открываем тестовую LONG позицию"""
        entry_price = self.close
        
        # Очень маленькие уровни для теста
        stop_loss_price = entry_price * 0.998   # -0.2%
        take_profit_price = entry_price * 1.004  # +0.4%
        
        # Минимальный размер позиции
        qty = 0.001  # 0.001 BTC = очень маленько для теста
        
        # Размещаем ордера
        self.buy = qty, entry_price
        self.stop_loss = qty, stop_loss_price  
        self.take_profit = qty, take_profit_price
        
        # Обновляем состояние
        self.last_signal_bar = self.index
        
        # Подробное логирование для теста
        self.log(f"🚀 === TEST LONG OPENED ===")
        self.log(f"Signal #{self.signal_counter} | Reason: {getattr(self, 'entry_reason', 'UNKNOWN')}")
        self.log(f"Size: {qty} BTC @ ${entry_price:.2f}")
        self.log(f"SL: ${stop_loss_price:.2f} (-0.2%) | TP: ${take_profit_price:.2f} (+0.4%)")
        self.log(f"Quick exit in {self.quick_exit_bars} bars ({self.quick_exit_bars} minutes)")
        
        if self.enable_ai_analysis:
            self.log("🤖 ИИ анализ будет запущен для этого сигнала...")
        else:
            self.log("⚠️ ИИ анализ ОТКЛЮЧЕН - проверьте настройки!")
    
    def go_short(self):
        """Открываем тестовую SHORT позицию"""
        entry_price = self.close
        
        # Очень маленькие уровни для теста
        stop_loss_price = entry_price * 1.002   # +0.2%
        take_profit_price = entry_price * 0.996  # -0.4%
        
        # Минимальный размер позиции
        qty = 0.001  # 0.001 BTC = очень маленько для теста
        
        # Размещаем ордера
        self.sell = qty, entry_price
        self.stop_loss = qty, stop_loss_price
        self.take_profit = qty, take_profit_price
        
        # Обновляем состояние
        self.last_signal_bar = self.index
        
        # Подробное логирование для теста
        self.log(f"🔻 === TEST SHORT OPENED ===")
        self.log(f"Signal #{self.signal_counter} | Reason: {getattr(self, 'entry_reason', 'UNKNOWN')}")
        self.log(f"Size: {qty} BTC @ ${entry_price:.2f}")
        self.log(f"SL: ${stop_loss_price:.2f} (+0.2%) | TP: ${take_profit_price:.2f} (-0.4%)")
        self.log(f"Quick exit in {self.quick_exit_bars} bars ({self.quick_exit_bars} minutes)")
        
        if self.enable_ai_analysis:
            self.log("🤖 ИИ анализ будет запущен для этого сигнала...")
        else:
            self.log("⚠️ ИИ анализ ОТКЛЮЧЕН - проверьте настройки!")
    
    def update_position(self):
        """Управление тестовой позицией"""
        if not self.position.is_open:
            return
        
        # Быстрый выход через несколько минут для теста
        position_age = self.index - self.last_signal_bar if self.last_signal_bar else 0
        
        if position_age >= self.quick_exit_bars:
            self.liquidate()
            self.log(f"⏰ TEST EXIT: Position closed after {position_age} minutes")
            self.log(f"P&L: ${self.position.pnl:.4f} (тестовый результат)")
    
    def on_close_position(self, order):
        """Обработка закрытия тестовой позиции"""
        pnl = self.position.pnl
        
        self.log(f"🏁 TEST POSITION CLOSED")
        self.log(f"   Exit price: ${order.price:.2f}")
        self.log(f"   P&L: ${pnl:.4f}")
        self.log(f"   Signal #{self.signal_counter} completed")
        self.log(f"   Ready for next test signal...")
        
        # Сбрасываем состояние
        if hasattr(self, 'entry_reason'):
            delattr(self, 'entry_reason')
    
    def before(self):
        """Мониторинг каждые 10 минут"""
        if self.index % 10 == 0 and self.index > 0:
            current_price = self.close
            price_change_10m = 0
            
            if self.index >= 10:
                price_10m_ago = self.candles[-10, 4]
                price_change_10m = (current_price - price_10m_ago) / price_10m_ago * 100
            
            self.log(f"📊 TEST MONITOR (Bar {self.index}):")
            self.log(f"   Current price: ${current_price:.2f}")
            self.log(f"   Change 10m: {price_change_10m:+.3f}%")
            self.log(f"   Signals generated: {self.signal_counter}")
            self.log(f"   Position: {'🟢 OPEN' if self.position.is_open else '⚪ CLOSED'}")
            
            if self.position.is_open:
                position_age = self.index - self.last_signal_bar if self.last_signal_bar else 0
                self.log(f"   Position age: {position_age} minutes | P&L: ${self.position.pnl:.4f}")
    
    # Переопределяем методы индикаторов (для теста они не нужны)
    def _get_current_indicators(self):
        """Простые индикаторы для ИИ анализа"""
        if self.index < 2:
            return {}
        
        current_price = self.close
        previous_price = self.candles[-2, 4]
        price_change = (current_price - previous_price) / previous_price * 100
        
        return {
            'current_price': current_price,
            'previous_price': previous_price,
            'price_change_1m': price_change,
            'signal_counter': self.signal_counter,
            'test_strategy': True
        }
