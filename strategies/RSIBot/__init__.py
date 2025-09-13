# strategies/RSIBot/__init__.py
from jesse.strategies import Strategy
import jesse.indicators as ta


class RSIBot(Strategy):
    """
    RSI стратегия v2.1 - Сбалансированная версия
    Умеренно строгие условия для стабильного результата
    """
    
    def __init__(self):
        super().__init__()
        
        # === ОСНОВНЫЕ ПАРАМЕТРЫ RSI ===
        self.rsi_period = 14
        self.oversold_level = 30      # Возвращаем к стандартным уровням
        self.overbought_level = 70    # Возвращаем к стандартным уровням
        self.rsi_exit_buffer = 5      # Стандартный буфер
        
        # === ПРОСТОЙ ФИЛЬТР ТРЕНДА ===
        self.sma_period = 20          # Короткая SMA для мягкого фильтра
        self.use_trend_filter = True  # Можно отключить при необходимости
        
        # === УПРАВЛЕНИЕ РИСКАМИ ===
        self.stop_loss_percent = 1.8  
        self.take_profit_percent = 3.6 # Соотношение 1:2
        self.risk_percent = 1.0       
        self.max_holding_hours = 36   
        
        # === КОНТРОЛЬ АКТИВНОСТИ ===
        self.max_consecutive_losses = 4  # Пауза только после 4 убытков
        self.min_gap_between_trades = 2  # Минимум 2 часа между сделками
        
        # Переменные состояния
        self.entry_price = None
        self.entry_bar = None
        self.position_type = None
        self.consecutive_losses = 0
        self.last_trade_bar = None
        
        self.log(f"=== RSI Bot v2.1 (Balanced) ===")
        self.log(f"RSI: {self.oversold_level}/{self.overbought_level}")
        self.log(f"Risk: {self.risk_percent}%, SL: {self.stop_loss_percent}%, TP: {self.take_profit_percent}%")

    @property
    def rsi(self):
        """RSI индикатор"""
        return ta.rsi(self.candles, period=self.rsi_period)
    
    @property 
    def rsi_previous(self):
        """RSI предыдущей свечи"""
        if self.index >= 1:
            return ta.rsi(self.candles[:-1], period=self.rsi_period)
        return 50.0
    
    @property
    def sma(self):
        """Короткая скользящая средняя"""
        return ta.sma(self.candles, period=self.sma_period)
    
    def _trend_allows_long(self):
        """Проверка тренда для покупки (мягкий фильтр)"""
        if not self.use_trend_filter:
            return True
        # Простое условие: цена выше SMA20
        return self.close > self.sma
    
    def _trend_allows_short(self):
        """Проверка тренда для продажи (мягкий фильтр)"""
        if not self.use_trend_filter:
            return True
        # Простое условие: цена ниже SMA20
        return self.close < self.sma
    
    def _can_trade(self):
        """Базовые проверки возможности торговли"""
        # Не торгуем если позиция открыта
        if self.position.is_open:
            return False
            
        # Недостаточно данных
        if self.index < max(self.rsi_period, self.sma_period) + 2:
            return False
            
        # Пауза после серии убытков
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False
            
        # Минимальный промежуток между сделками
        if (self.last_trade_bar is not None and 
            (self.index - self.last_trade_bar) < self.min_gap_between_trades):
            return False
            
        return True

    def should_long(self) -> bool:
        """
        Условия для покупки (сбалансированные):
        1. Базовые проверки пройдены
        2. RSI был в зоне перепроданности (<=30)
        3. RSI восстанавливается (>35)
        4. Тренд не против нас (цена > SMA20)
        """
        if not self._can_trade():
            return False
        
        current_rsi = self.rsi
        prev_rsi = self.rsi_previous
        
        # RSI условия
        was_oversold = prev_rsi <= self.oversold_level
        is_recovering = current_rsi > (self.oversold_level + self.rsi_exit_buffer)
        
        # Фильтр тренда (мягкий)
        trend_ok = self._trend_allows_long()
        
        if was_oversold and is_recovering and trend_ok:
            self.log(f"🟢 LONG: RSI {prev_rsi:.1f}→{current_rsi:.1f}, Price: {self.close:.2f}")
            return True
            
        return False
    
    def should_short(self) -> bool:
        """
        Условия для продажи (сбалансированные):
        1. Базовые проверки пройдены
        2. RSI был в зоне перекупленности (>=70)
        3. RSI снижается (<65)
        4. Тренд не против нас (цена < SMA20)
        """
        if not self._can_trade():
            return False
            
        current_rsi = self.rsi
        prev_rsi = self.rsi_previous
        
        # RSI условия
        was_overbought = prev_rsi >= self.overbought_level
        is_declining = current_rsi < (self.overbought_level - self.rsi_exit_buffer)
        
        # Фильтр тренда (мягкий)
        trend_ok = self._trend_allows_short()
        
        if was_overbought and is_declining and trend_ok:
            self.log(f"🔴 SHORT: RSI {prev_rsi:.1f}→{current_rsi:.1f}, Price: {self.close:.2f}")
            return True
            
        return False
    
    def should_cancel_entry(self) -> bool:
        return False
    
    def _calculate_position_size(self, entry_price, stop_loss_price):
        """Расчёт размера позиции на основе риска"""
        risk_amount = self.available_margin * (self.risk_percent / 100)
        price_diff = abs(entry_price - stop_loss_price)
        
        if price_diff > 0:
            qty = risk_amount / price_diff
            # Ограничиваем максимальным размером (85% от капитала)
            max_qty = (self.available_margin * 0.85) / entry_price
            qty = min(qty, max_qty)
            return max(qty, 0.001)  # Минимум 0.001
        else:
            return 0.001
    
    def go_long(self):
        """Открытие длинной позиции"""
        self.log(f"=== OPENING LONG POSITION ===")
        
        entry_price = self.close
        stop_loss_price = entry_price * (1 - self.stop_loss_percent / 100)
        take_profit_price = entry_price * (1 + self.take_profit_percent / 100)
        
        qty = self._calculate_position_size(entry_price, stop_loss_price)
        
        # Размещаем ордера
        self.buy = qty, entry_price
        self.stop_loss = qty, stop_loss_price
        self.take_profit = qty, take_profit_price
        
        # Сохраняем информацию о сделке
        self.entry_price = entry_price
        self.entry_bar = self.index
        self.position_type = 'LONG'
        self.last_trade_bar = self.index
        
        # Логирование
        risk_amount = qty * (entry_price - stop_loss_price)
        potential_profit = qty * (take_profit_price - entry_price)
        
        self.log(f"Size: {qty:.4f} BTC")
        self.log(f"Entry: ${entry_price:.2f}")
        self.log(f"Stop Loss: ${stop_loss_price:.2f} (-{self.stop_loss_percent}%)")
        self.log(f"Take Profit: ${take_profit_price:.2f} (+{self.take_profit_percent}%)")
        self.log(f"Risk: ${risk_amount:.2f} | Potential: ${potential_profit:.2f}")
        self.log(f"RSI: {self.rsi:.1f}")
    
    def go_short(self):
        """Открытие короткой позиции"""
        self.log(f"=== OPENING SHORT POSITION ===")
        
        entry_price = self.close
        stop_loss_price = entry_price * (1 + self.stop_loss_percent / 100)
        take_profit_price = entry_price * (1 - self.take_profit_percent / 100)
        
        qty = self._calculate_position_size(entry_price, stop_loss_price)
        
        # Размещаем ордера
        self.sell = qty, entry_price
        self.stop_loss = qty, stop_loss_price
        self.take_profit = qty, take_profit_price
        
        # Сохраняем информацию о сделке
        self.entry_price = entry_price
        self.entry_bar = self.index
        self.position_type = 'SHORT'
        self.last_trade_bar = self.index
        
        # Логирование
        risk_amount = qty * (stop_loss_price - entry_price)
        potential_profit = qty * (entry_price - take_profit_price)
        
        self.log(f"Size: {qty:.4f} BTC")
        self.log(f"Entry: ${entry_price:.2f}")
        self.log(f"Stop Loss: ${stop_loss_price:.2f} (+{self.stop_loss_percent}%)")
        self.log(f"Take Profit: ${take_profit_price:.2f} (-{self.take_profit_percent}%)")
        self.log(f"Risk: ${risk_amount:.2f} | Potential: ${potential_profit:.2f}")
        self.log(f"RSI: {self.rsi:.1f}")
    
    def update_position(self):
        """Управление открытой позицией"""
        if not self.position.is_open:
            return
        
        current_rsi = self.rsi
        should_close = False
        close_reason = ""
        
        # === ВЫХОД ПО RSI ===
        if self.position_type == 'LONG':
            # Закрываем LONG при достижении перекупленности
            if current_rsi >= self.overbought_level:
                should_close = True
                close_reason = f"RSI overbought: {current_rsi:.1f}"
                
        elif self.position_type == 'SHORT':
            # Закрываем SHORT при достижении перепроданности
            if current_rsi <= self.oversold_level:
                should_close = True
                close_reason = f"RSI oversold: {current_rsi:.1f}"
        
        # === ВЫХОД ПО ВРЕМЕНИ ===
        if self.entry_bar and (self.index - self.entry_bar) >= self.max_holding_hours:
            should_close = True
            close_reason = f"Max time: {self.max_holding_hours}h"
        
        # Закрываем позицию если есть основание
        if should_close:
            self.liquidate()
            self.log(f"🚪 Position closed: {close_reason}")
            self.log(f"Final P&L: ${self.position.pnl:.2f}")
            
            # Обновляем счётчик убытков
            if self.position.pnl < 0:
                self.consecutive_losses += 1
                self.log(f"⚠️  Consecutive losses: {self.consecutive_losses}")
                
                # Временное отключение фильтра тренда после серии убытков
                if self.consecutive_losses >= 3:
                    self.use_trend_filter = False
                    self.log("🔄 Trend filter disabled temporarily")
            else:
                self.consecutive_losses = 0
                self.use_trend_filter = True  # Включаем обратно фильтр
                self.log("✅ Profitable trade! Reset loss counter")
                
            self._reset_position_tracking()
    
    def _reset_position_tracking(self):
        """Сброс переменных отслеживания позиции"""
        self.entry_price = None
        self.entry_bar = None
        self.position_type = None
    
    def on_open_position(self, order):
        """Событие открытия позиции"""
        self.log(f"✅ Position opened: {order.qty:.4f} @ ${order.price:.2f}")
        self.log(f"Available margin: ${self.available_margin:.2f}")
    
    def on_close_position(self, order):
        """Событие закрытия позиции"""
        self.log(f"🔚 Position closed @ ${order.price:.2f}")
        self.log(f"Total P&L: ${self.position.pnl:.2f}")
        self.log(f"RSI at exit: {self.rsi:.1f}")
        self._reset_position_tracking()
    
    def before(self):
        """Отладочная информация (каждые 24 часа)"""
        if self.index % 24 == 0 and self.index >= max(self.rsi_period, self.sma_period):
            current_rsi = self.rsi
            trend_direction = "📈" if self.close > self.sma else "📉"
            
            # Определяем состояние рынка
            if current_rsi <= self.oversold_level:
                market_state = "OVERSOLD 🟢"
            elif current_rsi >= self.overbought_level:
                market_state = "OVERBOUGHT 🔴"
            else:
                market_state = "NEUTRAL ⚪"
            
            self.log(f"📊 Day {self.index//24}: RSI={current_rsi:.1f} {trend_direction} | {market_state}")
            self.log(f"Price: ${self.close:.2f} | Losses: {self.consecutive_losses}")
            
            if self.position.is_open:
                hours_held = self.index - self.entry_bar if self.entry_bar else 0
                self.log(f"🎯 {self.position_type}: {hours_held}h | P&L: ${self.position.pnl:.2f}")
