# strategies/QualityTrader/__init__.py
from jesse.strategies import Strategy
import jesse.indicators as ta
import numpy as np


class QualityTrader(Strategy):
    """
    QUALITY OVER QUANTITY STRATEGY
    Цель: 1-2 качественные сделки в день с винрейтом 65%+
    Логика: Строгие условия + мультитаймфреймовый анализ + тренд-следование
    """
    
    def __init__(self):
        super().__init__()
        
        # === КОНСЕРВАТИВНЫЕ ИНДИКАТОРЫ ===
        self.ema_fast = 12          # Быстрая EMA
        self.ema_slow = 26          # Медленная EMA
        self.ema_trend = 50         # EMA для определения тренда
        self.rsi_period = 14        # Стандартный RSI
        self.atr_period = 14        # ATR для волатильности
        self.volume_ma_period = 20  # Объём
        
        # === СТРОГИЕ УСЛОВИЯ ВХОДА ===
        self.min_trend_strength = 0.5    # Минимальная сила тренда в %
        self.min_volume_ratio = 1.5      # Объём должен быть 1.5x выше среднего
        self.rsi_overbought = 70         # RSI перекупленность  
        self.rsi_oversold = 30           # RSI перепроданность
        self.min_candle_body = 0.3       # Минимум 0.3% размер свечи
        self.trend_confirmation_bars = 3 # Подтверждение тренда на 3 свечах
        
        # === КАЧЕСТВЕННОЕ УПРАВЛЕНИЕ РИСКАМИ ===
        self.risk_percent = 0.5          # Низкий риск на сделку
        self.atr_stop_multiplier = 2.0   # Консервативный стоп
        self.min_rr_ratio = 2.5          # Высокое соотношение риск/прибыль
        self.max_holding_hours = 24      # Максимум 24 часа в позиции
        
        # === ОГРАНИЧЕНИЯ ДЛЯ КАЧЕСТВА ===
        self.max_daily_trades = 2        # МАКСИМУМ 2 СДЕЛКИ В ДЕНЬ!
        self.min_gap_hours = 4           # Минимум 4 часа между сделками
        self.max_consecutive_losses = 2  # Пауза после 2 убытков
        self.min_profit_to_trade = 20    # Торгуем только если потенциал >$20
        
        # === ФИЛЬТРЫ КАЧЕСТВА ===
        self.require_trend_alignment = True   # Обязательное совпадение с трендом
        self.require_volume_confirmation = True # Обязательное подтверждение объёмом
        self.require_rsi_filter = True       # Обязательный RSI фильтр
        self.avoid_choppy_market = True      # Избегаем боковых движений
        
        # === СОСТОЯНИЕ ===
        self.entry_bar = None
        self.position_type = None
        self.daily_trades_count = 0
        self.last_day = None
        self.last_trade_bar = None
        self.consecutive_losses = 0
        self.market_regime = "UNKNOWN"
        
        self.log(f"=== QUALITY TRADER INITIALIZED ===")
        self.log(f"Philosophy: QUALITY > QUANTITY")
        self.log(f"Target: 1-2 high-quality trades per day")
        self.log(f"Risk: {self.risk_percent}% | Min R:R: {self.min_rr_ratio}")
        self.log(f"Max daily trades: {self.max_daily_trades}")

    # === ИНДИКАТОРЫ ===
    @property
    def ema12(self):
        return ta.ema(self.candles, period=self.ema_fast)
    
    @property
    def ema26(self):
        return ta.ema(self.candles, period=self.ema_slow)
    
    @property
    def ema50(self):
        return ta.ema(self.candles, period=self.ema_trend)
    
    @property
    def rsi(self):
        return ta.rsi(self.candles, period=self.rsi_period)
    
    @property
    def atr(self):
        return ta.atr(self.candles, period=self.atr_period)
    
    @property
    def volume_ma(self):
        return ta.sma(self.candles[:, 5], period=self.volume_ma_period)
    
    @property
    def current_volume(self):
        return self.candles[-1, 5]
    
    # === АНАЛИЗ ТРЕНДА (КАЧЕСТВЕННЫЙ) ===
    def _get_trend_direction(self):
        """Определяем направление тренда с подтверждением"""
        # Основной тренд по EMA50
        price_vs_ema50 = (self.close - self.ema50) / self.ema50 * 100
        
        # Краткосрочный тренд
        ema12_vs_ema26 = (self.ema12 - self.ema26) / self.ema26 * 100
        
        # Сила тренда
        if price_vs_ema50 > self.min_trend_strength and ema12_vs_ema26 > 0:
            return "STRONG_UP"
        elif price_vs_ema50 < -self.min_trend_strength and ema12_vs_ema26 < 0:
            return "STRONG_DOWN"
        elif abs(price_vs_ema50) < self.min_trend_strength:
            return "SIDEWAYS"
        else:
            return "WEAK_TREND"
    
    def _confirm_trend_on_multiple_bars(self, direction):
        """Подтверждаем тренд на нескольких свечах"""
        if self.index < self.trend_confirmation_bars:
            return False
            
        confirmations = 0
        for i in range(self.trend_confirmation_bars):
            if self.index >= i + 1:
                # Проверяем направление EMA на прошлых свечах
                past_candles = self.candles[:-i-1] if i > 0 else self.candles
                past_ema12 = ta.ema(past_candles, period=self.ema_fast)
                past_ema26 = ta.ema(past_candles, period=self.ema_slow)
                
                if direction == "UP" and past_ema12 > past_ema26:
                    confirmations += 1
                elif direction == "DOWN" and past_ema12 < past_ema26:
                    confirmations += 1
        
        return confirmations >= (self.trend_confirmation_bars - 1)
    
    def _is_market_choppy(self):
        """Определяем боковой/хаотичный рынок"""
        # Анализируем последние 10 свечей
        if self.index < 10:
            return False
            
        recent_highs = self.candles[-10:, 2]  # High prices
        recent_lows = self.candles[-10:, 3]   # Low prices
        
        price_range = (max(recent_highs) - min(recent_lows)) / self.close * 100
        
        # Если диапазон меньше 2% - рынок боковой
        return price_range < 2.0
    
    def _update_daily_counter(self):
        """Обновляем счётчик дневных сделок"""
        current_day = self.index // 24  # 24 часовые свечи = 1 день
        if self.last_day != current_day:
            self.daily_trades_count = 0
            self.last_day = current_day
            if current_day > 0:  # Не логируем в первый день
                self.log(f"📅 New day {current_day}: Reset daily counter")
    
    def _has_quality_volume(self):
        """Проверяем качество объёма"""
        if not self.require_volume_confirmation:
            return True
            
        volume_ratio = self.current_volume / self.volume_ma
        return volume_ratio >= self.min_volume_ratio
    
    def _is_strong_candle(self):
        """Проверяем силу свечи"""
        body_percent = abs(self.close - self.open) / self.open * 100
        return body_percent >= self.min_candle_body
    
    def _calculate_potential_profit(self, entry_price, is_long=True):
        """Рассчитываем потенциальную прибыль сделки"""
        atr_value = self.atr
        stop_distance = atr_value * self.atr_stop_multiplier
        
        if is_long:
            stop_loss = entry_price - stop_distance
            take_profit = entry_price + (stop_distance * self.min_rr_ratio)
        else:
            stop_loss = entry_price + stop_distance
            take_profit = entry_price - (stop_distance * self.min_rr_ratio)
        
        risk_amount = self.available_margin * (self.risk_percent / 100)
        price_diff = abs(entry_price - stop_loss)
        
        if price_diff > 0:
            qty = risk_amount / price_diff
            potential_profit = qty * abs(take_profit - entry_price)
            return potential_profit
        
        return 0
    
    def _can_trade(self):
        """СТРОГИЕ условия для торговли"""
        self._update_daily_counter()
        
        # Недостаточно данных
        if self.index < max(self.ema_trend, self.volume_ma_period, self.trend_confirmation_bars) + 10:
            return False
        
        # Уже есть позиция
        if self.position.is_open:
            return False
        
        # Превышен дневной лимит
        if self.daily_trades_count >= self.max_daily_trades:
            return False
        
        # Слишком много убытков подряд
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.log(f"⏸️  Trading paused: {self.consecutive_losses} consecutive losses")
            return False
        
        # Минимальный промежуток между сделками
        if (self.last_trade_bar is not None and 
            (self.index - self.last_trade_bar) < self.min_gap_hours):
            return False
        
        # Избегаем хаотичного рынка
        if self.avoid_choppy_market and self._is_market_choppy():
            return False
        
        return True

    # === КАЧЕСТВЕННЫЕ УСЛОВИЯ ВХОДА ===
    def should_long(self) -> bool:
        """
        СТРОГИЕ условия для LONG:
        1. Сильный восходящий тренд (EMA12 > EMA26 > EMA50)
        2. Цена выше EMA50 на минимум 0.5%
        3. RSI в зоне 30-70 (не экстремальные значения)
        4. Подтверждение тренда на 3 свечах
        5. Объём выше среднего в 1.5 раза
        6. Сильная зелёная свеча (>0.3%)
        7. Потенциальная прибыль >$20
        """
        if not self._can_trade():
            return False
        
        # === АНАЛИЗ ТРЕНДА ===
        trend = self._get_trend_direction()
        if self.require_trend_alignment and trend != "STRONG_UP":
            return False
        
        trend_confirmed = self._confirm_trend_on_multiple_bars("UP")
        if not trend_confirmed:
            return False
        
        # === ТЕХНИЧЕСКИЕ УСЛОВИЯ ===
        ema_alignment = self.ema12 > self.ema26 > self.ema50
        price_above_trend = self.close > self.ema50
        
        # === RSI ФИЛЬТР ===
        rsi_ok = True
        if self.require_rsi_filter:
            rsi_ok = self.rsi_oversold <= self.rsi <= self.rsi_overbought
        
        # === ОБЪЁМ И СВЕЧА ===
        volume_ok = self._has_quality_volume()
        strong_candle = self._is_strong_candle()
        green_candle = self.close > self.open
        
        # === ПОТЕНЦИАЛЬНАЯ ПРИБЫЛЬ ===
        potential_profit = self._calculate_potential_profit(self.close, is_long=True)
        profit_ok = potential_profit >= self.min_profit_to_trade
        
        # ПРОВЕРЯЕМ ВСЕ УСЛОВИЯ
        all_conditions = [
            ema_alignment,
            price_above_trend, 
            rsi_ok,
            volume_ok,
            strong_candle,
            green_candle,
            profit_ok
        ]
        
        if all(all_conditions):
            self.log(f"🟢 HIGH-QUALITY LONG SIGNAL:")
            self.log(f"   Trend: {trend}")
            self.log(f"   Price: ${self.close:.2f} (EMA50: ${self.ema50:.2f})")
            self.log(f"   RSI: {self.rsi:.1f}")
            self.log(f"   Volume: {self.current_volume/self.volume_ma:.1f}x avg")
            self.log(f"   Potential profit: ${potential_profit:.2f}")
            self.log(f"   Daily trades: {self.daily_trades_count}/{self.max_daily_trades}")
            return True
        
        return False
    
    def should_short(self) -> bool:
        """
        СТРОГИЕ условия для SHORT:
        1. Сильный нисходящий тренд (EMA12 < EMA26 < EMA50)
        2. Цена ниже EMA50 на минимум 0.5%
        3. RSI в зоне 30-70 (не экстремальные значения)
        4. Подтверждение тренда на 3 свечах
        5. Объём выше среднего в 1.5 раза
        6. Сильная красная свеча (>0.3%)
        7. Потенциальная прибыль >$20
        """
        if not self._can_trade():
            return False
        
        # === АНАЛИЗ ТРЕНДА ===
        trend = self._get_trend_direction()
        if self.require_trend_alignment and trend != "STRONG_DOWN":
            return False
        
        trend_confirmed = self._confirm_trend_on_multiple_bars("DOWN")
        if not trend_confirmed:
            return False
        
        # === ТЕХНИЧЕСКИЕ УСЛОВИЯ ===
        ema_alignment = self.ema12 < self.ema26 < self.ema50
        price_below_trend = self.close < self.ema50
        
        # === RSI ФИЛЬТР ===
        rsi_ok = True
        if self.require_rsi_filter:
            rsi_ok = self.rsi_oversold <= self.rsi <= self.rsi_overbought
        
        # === ОБЪЁМ И СВЕЧА ===
        volume_ok = self._has_quality_volume()
        strong_candle = self._is_strong_candle()
        red_candle = self.close < self.open
        
        # === ПОТЕНЦИАЛЬНАЯ ПРИБЫЛЬ ===
        potential_profit = self._calculate_potential_profit(self.close, is_long=False)
        profit_ok = potential_profit >= self.min_profit_to_trade
        
        # ПРОВЕРЯЕМ ВСЕ УСЛОВИЯ
        all_conditions = [
            ema_alignment,
            price_below_trend,
            rsi_ok,
            volume_ok,
            strong_candle,
            red_candle,
            profit_ok
        ]
        
        if all(all_conditions):
            self.log(f"🔴 HIGH-QUALITY SHORT SIGNAL:")
            self.log(f"   Trend: {trend}")
            self.log(f"   Price: ${self.close:.2f} (EMA50: ${self.ema50:.2f})")
            self.log(f"   RSI: {self.rsi:.1f}")
            self.log(f"   Volume: {self.current_volume/self.volume_ma:.1f}x avg")
            self.log(f"   Potential profit: ${potential_profit:.2f}")
            self.log(f"   Daily trades: {self.daily_trades_count}/{self.max_daily_trades}")
            return True
        
        return False
    
    def should_cancel_entry(self) -> bool:
        return False
    
    # === КАЧЕСТВЕННОЕ УПРАВЛЕНИЕ ПОЗИЦИЯМИ ===
    def _calculate_position_size(self, entry_price, stop_loss_price):
        """Консервативный расчёт размера позиции"""
        risk_amount = self.available_margin * (self.risk_percent / 100)
        price_diff = abs(entry_price - stop_loss_price)
        
        if price_diff > 0:
            qty = risk_amount / price_diff
            # Консервативное ограничение размера
            max_qty = (self.available_margin * 0.7) / entry_price  # Только 70% капитала
            return min(qty, max_qty, 0.1)  # Максимум 0.1 BTC
        else:
            return 0.001
    
    def go_long(self):
        """Открытие качественной LONG позиции"""
        entry_price = self.close
        
        # Консервативный стоп на основе ATR
        atr_value = self.atr
        stop_loss_price = entry_price - (atr_value * self.atr_stop_multiplier)
        
        # Высокий тейк-профит (минимум 1:2.5)
        risk_distance = entry_price - stop_loss_price
        take_profit_price = entry_price + (risk_distance * self.min_rr_ratio)
        
        qty = self._calculate_position_size(entry_price, stop_loss_price)
        
        # Размещаем ордера
        self.buy = qty, entry_price
        self.stop_loss = qty, stop_loss_price
        self.take_profit = qty, take_profit_price
        
        # Обновляем состояние
        self.entry_bar = self.index
        self.position_type = 'LONG'
        self.last_trade_bar = self.index
        self.daily_trades_count += 1
        
        # Рассчитываем потенциалы
        risk_amount = qty * risk_distance
        potential_profit = qty * (take_profit_price - entry_price)
        
        self.log(f"=== QUALITY LONG POSITION #{self.daily_trades_count} ===")
        self.log(f"Entry: {qty:.4f} BTC @ ${entry_price:.2f}")
        self.log(f"Stop Loss: ${stop_loss_price:.2f} (ATR: ${atr_value:.2f})")
        self.log(f"Take Profit: ${take_profit_price:.2f}")
        self.log(f"Risk: ${risk_amount:.2f} | Potential: ${potential_profit:.2f}")
        self.log(f"Risk:Reward = 1:{self.min_rr_ratio}")
    
    def go_short(self):
        """Открытие качественной SHORT позиции"""
        entry_price = self.close
        
        # Консервативный стоп на основе ATR
        atr_value = self.atr
        stop_loss_price = entry_price + (atr_value * self.atr_stop_multiplier)
        
        # Высокий тейк-профит (минимум 1:2.5)
        risk_distance = stop_loss_price - entry_price
        take_profit_price = entry_price - (risk_distance * self.min_rr_ratio)
        
        qty = self._calculate_position_size(entry_price, stop_loss_price)
        
        # Размещаем ордера
        self.sell = qty, entry_price
        self.stop_loss = qty, stop_loss_price
        self.take_profit = qty, take_profit_price
        
        # Обновляем состояние
        self.entry_bar = self.index
        self.position_type = 'SHORT'
        self.last_trade_bar = self.index
        self.daily_trades_count += 1
        
        # Рассчитываем потенциалы
        risk_amount = qty * risk_distance
        potential_profit = qty * (entry_price - take_profit_price)
        
        self.log(f"=== QUALITY SHORT POSITION #{self.daily_trades_count} ===")
        self.log(f"Entry: {qty:.4f} BTC @ ${entry_price:.2f}")
        self.log(f"Stop Loss: ${stop_loss_price:.2f} (ATR: ${atr_value:.2f})")
        self.log(f"Take Profit: ${take_profit_price:.2f}")
        self.log(f"Risk: ${risk_amount:.2f} | Potential: ${potential_profit:.2f}")
        self.log(f"Risk:Reward = 1:{self.min_rr_ratio}")
    
    def update_position(self):
        """Управление качественной позицией"""
        if not self.position.is_open:
            return
        
        # Принудительное закрытие по времени
        if self.entry_bar and (self.index - self.entry_bar) >= self.max_holding_hours:
            self.liquidate()
            self.log(f"⏰ Position closed by time limit ({self.max_holding_hours}h)")
            self.log(f"P&L: ${self.position.pnl:.2f}")
            self._reset_position()
    
    def _reset_position(self):
        """Сброс переменных позиции"""
        self.entry_bar = None
        self.position_type = None
    
    def on_close_position(self, order):
        """Обработка закрытия позиции"""
        pnl = self.position.pnl
        
        # Обновляем счётчик убытков
        if pnl < 0:
            self.consecutive_losses += 1
            self.log(f"❌ Quality Loss: ${pnl:.2f}")
            self.log(f"   Consecutive losses: {self.consecutive_losses}")
            
            # После 2 убытков - анализируем рынок
            if self.consecutive_losses >= self.max_consecutive_losses:
                self.log(f"⏸️  Pausing trading after {self.consecutive_losses} losses")
                self.log(f"   Will resume after market analysis...")
        else:
            self.consecutive_losses = 0
            self.log(f"✅ Quality Profit: ${pnl:.2f}")
            self.log(f"   Reset loss counter - excellent trade!")
        
        self.log(f"🔚 Position closed @ ${order.price:.2f}")
        self.log(f"   Daily trades: {self.daily_trades_count}/{self.max_daily_trades}")
        self._reset_position()
    
    def before(self):
        """Качественный мониторинг (каждые 6 часов)"""
        if self.index % 6 == 0 and self.index >= self.ema_trend:
            self._update_daily_counter()
            
            trend = self._get_trend_direction()
            is_choppy = self._is_market_choppy()
            
            # Состояние рынка
            market_emoji = {
                "STRONG_UP": "🚀",
                "STRONG_DOWN": "🐻", 
                "WEAK_TREND": "⚪",
                "SIDEWAYS": "↔️"
            }
            
            self.log(f"📊 Quality Check (Hour {self.index}):")
            self.log(f"   Price: ${self.close:.2f} | Trend: {trend} {market_emoji.get(trend, '❓')}")
            self.log(f"   RSI: {self.rsi:.1f} | Vol: {self.current_volume/self.volume_ma:.1f}x")
            self.log(f"   Choppy: {'Yes' if is_choppy else 'No'} | Trades: {self.daily_trades_count}/2")
            self.log(f"   Consecutive losses: {self.consecutive_losses}")
            
            if self.position.is_open:
                hours_held = self.index - self.entry_bar if self.entry_bar else 0
                self.log(f"   Position: {self.position_type} {hours_held}h | P&L: ${self.position.pnl:.2f}")
