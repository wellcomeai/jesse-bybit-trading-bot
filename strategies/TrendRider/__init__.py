# strategies/TrendRider/__init__.py
from jesse.strategies import Strategy
import jesse.indicators as ta
import numpy as np


class TrendRider(Strategy):
    """
    TREND RIDER - Продуманная трендовая стратегия
    
    Философия: "Тренд твой друг до самого конца"
    Логика: Покупаем откаты в растущем тренде, продаем отскоки в падающем
    
    Ключевые принципы:
    1. Торгуем ТОЛЬКО по тренду (никогда против)
    2. EMA200 - главный арбитр тренда
    3. Входы на откатах к EMA50
    4. Строгие фильтры качества
    5. Консервативное управление рисками
    """
    
    def __init__(self):
        super().__init__()
        
        # === ТРЕНДОВЫЕ ИНДИКАТОРЫ ===
        self.ema_fast = 21          # Быстрая EMA для сигналов
        self.ema_medium = 50        # Средняя EMA для входов
        self.ema_trend = 200        # ГЛАВНЫЙ фильтр тренда
        self.rsi_period = 14        # RSI для откатов
        self.atr_period = 20        # ATR для стопов
        self.volume_ma_period = 20  # Средний объём
        
        # === ОПРЕДЕЛЕНИЕ ТРЕНДА ===
        self.trend_strength_min = 1.0      # Минимум 1% цена от EMA200
        self.ema_alignment_min = 0.5       # Минимальное расстояние между EMA
        self.trend_confirmation_bars = 5   # Подтверждение тренда на барах
        
        # === УСЛОВИЯ ВХОДА (КОНСЕРВАТИВНЫЕ) ===
        self.rsi_oversold_bull = 35        # RSI для покупки в бычьем тренде
        self.rsi_overbought_bear = 65      # RSI для продажи в медвежьем тренде
        self.rsi_extreme_bull = 25         # Экстремально перепродан
        self.rsi_extreme_bear = 75         # Экстремально перекуплен
        self.min_volume_ratio = 1.2        # Минимальный объём
        self.volume_spike_ratio = 2.0      # Всплеск объёма
        
        # === УПРАВЛЕНИЕ РИСКАМИ ===
        self.risk_percent = 0.8            # Консервативный риск
        self.atr_stop_multiplier = 2.0     # Стоп = 2x ATR
        self.profit_target_ratio = 2.5     # Профит = 2.5x риск (1:2.5)
        self.max_holding_hours = 48        # Максимум 48 часов
        
        # === КОНТРОЛЬ АКТИВНОСТИ ===
        self.max_daily_trades = 2          # Максимум 2 сделки в день
        self.min_gap_hours = 6             # Минимум 6 часов между сделками  
        self.max_consecutive_losses = 3    # Пауза после 3 убытков
        
        # === ФИЛЬТРЫ КАЧЕСТВА ===
        self.min_candle_body = 0.4         # Минимум 0.4% размер свечи
        self.avoid_weekend_trades = True   # Избегать торговли в выходные
        self.require_trend_momentum = True  # Требовать импульс тренда
        
        # === СОСТОЯНИЕ ===
        self.entry_bar = None
        self.position_type = None
        self.daily_trades_count = 0
        self.last_day = None
        self.last_trade_bar = None
        self.consecutive_losses = 0
        self.current_trend = "NEUTRAL"     # BULL, BEAR, NEUTRAL
        self.trend_strength = 0
        
        self.log(f"=== TREND RIDER INITIALIZED ===")
        self.log(f"Philosophy: Trend is your friend!")
        self.log(f"EMA Trend Filter: {self.ema_trend}")
        self.log(f"Risk: {self.risk_percent}% | R:R = 1:{self.profit_target_ratio}")
        self.log(f"Max daily trades: {self.max_daily_trades}")

    # === ИНДИКАТОРЫ ===
    @property
    def ema21(self):
        return ta.ema(self.candles, period=self.ema_fast)
    
    @property
    def ema50(self):
        return ta.ema(self.candles, period=self.ema_medium)
    
    @property
    def ema200(self):
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
    
    # === АНАЛИЗ ТРЕНДА (КЛЮЧЕВАЯ ЛОГИКА) ===
    def _analyze_trend(self):
        """Определяем текущий тренд и его силу"""
        if self.index < self.ema_trend + 10:
            self.current_trend = "NEUTRAL"
            self.trend_strength = 0
            return
        
        # Расстояние цены от EMA200
        price_vs_ema200 = (self.close - self.ema200) / self.ema200 * 100
        
        # Порядок EMA
        ema_bull_alignment = self.ema21 > self.ema50 > self.ema200
        ema_bear_alignment = self.ema21 < self.ema50 < self.ema200
        
        # Подтверждение тренда на последних барах
        trend_confirmed = self._confirm_trend_direction()
        
        # Определяем тренд
        if (price_vs_ema200 > self.trend_strength_min and 
            ema_bull_alignment and trend_confirmed):
            self.current_trend = "BULL"
            self.trend_strength = min(abs(price_vs_ema200), 10)  # Макс 10%
        elif (price_vs_ema200 < -self.trend_strength_min and 
              ema_bear_alignment and trend_confirmed):
            self.current_trend = "BEAR" 
            self.trend_strength = min(abs(price_vs_ema200), 10)
        else:
            self.current_trend = "NEUTRAL"
            self.trend_strength = 0
    
    def _confirm_trend_direction(self):
        """Подтверждаем направление тренда на нескольких барах"""
        if self.index < self.trend_confirmation_bars:
            return False
        
        bull_bars = 0
        bear_bars = 0
        
        for i in range(self.trend_confirmation_bars):
            if i == 0:
                close_price = self.close
                ema200_value = self.ema200
            else:
                close_price = self.candles[-i-1, 4]
                past_candles = self.candles[:-i] if i > 0 else self.candles
                ema200_value = ta.ema(past_candles, period=self.ema_trend)
            
            if close_price > ema200_value:
                bull_bars += 1
            else:
                bear_bars += 1
        
        # Тренд подтвержден если 80%+ баров в одном направлении
        confirmation_threshold = int(self.trend_confirmation_bars * 0.8)
        return bull_bars >= confirmation_threshold or bear_bars >= confirmation_threshold
    
    def _is_pullback_to_ema50(self):
        """Проверяем откат к EMA50"""
        distance_to_ema50 = abs(self.close - self.ema50) / self.close * 100
        return distance_to_ema50 < 1.0  # В пределах 1% от EMA50
    
    def _has_trend_momentum(self):
        """Проверяем импульс тренда"""
        if not self.require_trend_momentum:
            return True
        
        # Проверяем последние 3 свечи
        if self.index < 3:
            return False
        
        recent_closes = [
            self.candles[-3, 4],  # 3 свечи назад
            self.candles[-2, 4],  # 2 свечи назад  
            self.close            # Текущая
        ]
        
        if self.current_trend == "BULL":
            # В бычьем тренде ищем восстановление после отката
            return recent_closes[2] > recent_closes[0]
        elif self.current_trend == "BEAR":
            # В медвежьем тренде ищем продолжение снижения
            return recent_closes[2] < recent_closes[0]
        
        return False
    
    def _update_daily_counter(self):
        """Обновляем счётчик дневных сделок"""
        current_day = self.index // 24  # 24 часовые свечи = 1 день
        if self.last_day != current_day:
            if self.daily_trades_count > 0:
                self.log(f"📅 Day {current_day}: {self.daily_trades_count} trades | Trend: {self.current_trend}")
            self.daily_trades_count = 0
            self.last_day = current_day
    
    def _has_quality_volume(self):
        """Проверяем качество объёма"""
        base_volume = self.current_volume > (self.volume_ma * self.min_volume_ratio)
        volume_spike = self.current_volume > (self.volume_ma * self.volume_spike_ratio)
        return base_volume or volume_spike
    
    def _is_strong_candle(self):
        """Проверяем силу свечи"""
        body_percent = abs(self.close - self.open) / self.open * 100
        return body_percent >= self.min_candle_body
    
    def _can_trade(self):
        """Базовые условия для торговли"""
        self._update_daily_counter()
        self._analyze_trend()
        
        # Недостаточно данных
        if self.index < self.ema_trend + 20:
            return False
        
        # Только в трендовом рынке
        if self.current_trend == "NEUTRAL":
            return False
        
        # Уже есть позиция
        if self.position.is_open:
            return False
        
        # Превышен дневной лимит
        if self.daily_trades_count >= self.max_daily_trades:
            return False
        
        # Слишком много убытков подряд
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False
        
        # Минимальный промежуток между сделками
        if (self.last_trade_bar is not None and 
            (self.index - self.last_trade_bar) < self.min_gap_hours):
            return False
        
        # Качество объёма и свечи
        if not self._has_quality_volume() or not self._is_strong_candle():
            return False
        
        return True

    # === ТРЕНДОВЫЕ УСЛОВИЯ ВХОДА ===
    def should_long(self) -> bool:
        """
        LONG только в БЫЧЬЕМ тренде:
        
        1. Цена выше EMA200 (главное условие!)
        2. EMA21 > EMA50 > EMA200 (порядок EMA)
        3. RSI показывает откат (25-40)
        4. Откат к EMA50 (в пределах 1%)
        5. Импульс восстановления
        6. Качественный объём
        """
        if not self._can_trade():
            return False
        
        # КРИТИЧНО: только в бычьем тренде!
        if self.current_trend != "BULL":
            return False
        
        # Основные условия
        rsi_in_pullback = (self.rsi_extreme_bull <= self.rsi <= self.rsi_oversold_bull)
        near_ema50 = self._is_pullback_to_ema50()
        has_momentum = self._has_trend_momentum()
        green_candle = self.close > self.open
        
        # Дополнительное подтверждение силы тренда
        strong_trend = self.trend_strength >= 2.0  # Минимум 2% от EMA200
        
        if rsi_in_pullback and near_ema50 and has_momentum and green_candle and strong_trend:
            self.log(f"🚀 LONG: Bull Trend Pullback")
            self.log(f"   Price: ${self.close:.2f} vs EMA200: ${self.ema200:.2f}")
            self.log(f"   RSI: {self.rsi:.1f} | Trend Strength: {self.trend_strength:.1f}%")
            self.log(f"   EMA50 Distance: {abs(self.close - self.ema50)/self.close*100:.2f}%")
            self.entry_reason = "BULL_PULLBACK"
            return True
        
        return False
    
    def should_short(self) -> bool:
        """
        SHORT только в МЕДВЕЖЬЕМ тренде:
        
        1. Цена ниже EMA200 (главное условие!)
        2. EMA21 < EMA50 < EMA200 (порядок EMA)
        3. RSI показывает отскок (60-75)
        4. Отскок к EMA50 (в пределах 1%)
        5. Импульс продолжения падения
        6. Качественный объём
        """
        if not self._can_trade():
            return False
        
        # КРИТИЧНО: только в медвежьем тренде!
        if self.current_trend != "BEAR":
            return False
        
        # Основные условия
        rsi_in_bounce = (self.rsi_overbought_bear <= self.rsi <= self.rsi_extreme_bear)
        near_ema50 = self._is_pullback_to_ema50()
        has_momentum = self._has_trend_momentum()
        red_candle = self.close < self.open
        
        # Дополнительное подтверждение силы тренда
        strong_trend = self.trend_strength >= 2.0
        
        if rsi_in_bounce and near_ema50 and has_momentum and red_candle and strong_trend:
            self.log(f"🐻 SHORT: Bear Trend Bounce")
            self.log(f"   Price: ${self.close:.2f} vs EMA200: ${self.ema200:.2f}")
            self.log(f"   RSI: {self.rsi:.1f} | Trend Strength: {self.trend_strength:.1f}%")
            self.log(f"   EMA50 Distance: {abs(self.close - self.ema50)/self.close*100:.2f}%")
            self.entry_reason = "BEAR_BOUNCE"
            return True
        
        return False
    
    def should_cancel_entry(self) -> bool:
        return False
    
    # === ТРЕНДОВОЕ УПРАВЛЕНИЕ ПОЗИЦИЯМИ ===
    def _calculate_position_size(self, entry_price, stop_loss_price):
        """Расчёт размера позиции с учётом силы тренда"""
        base_risk = self.available_margin * (self.risk_percent / 100)
        
        # Увеличиваем размер для сильных трендов
        trend_multiplier = 1.0 + (self.trend_strength / 20)  # Макс +50%
        risk_amount = base_risk * min(trend_multiplier, 1.5)
        
        price_diff = abs(entry_price - stop_loss_price)
        
        if price_diff > 0:
            qty = risk_amount / price_diff
            max_qty = (self.available_margin * 0.7) / entry_price
            return min(qty, max_qty, 0.1)
        else:
            return 0.001
    
    def go_long(self):
        """Открытие трендовой LONG позиции"""
        entry_price = self.close
        
        # Стоп-лосс по ATR
        atr_stop = self.atr * self.atr_stop_multiplier
        stop_loss_price = entry_price - atr_stop
        
        # Тейк-профит по соотношению риск/прибыль
        risk_distance = entry_price - stop_loss_price
        take_profit_price = entry_price + (risk_distance * self.profit_target_ratio)
        
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
        
        # Логирование
        risk_amount = qty * risk_distance
        potential_profit = qty * (take_profit_price - entry_price)
        
        self.log(f"=== TREND LONG #{self.daily_trades_count} ===")
        self.log(f"Reason: {getattr(self, 'entry_reason', 'UNKNOWN')}")
        self.log(f"Size: {qty:.4f} @ ${entry_price:.2f}")
        self.log(f"Stop: ${stop_loss_price:.2f} | Take: ${take_profit_price:.2f}")
        self.log(f"Risk: ${risk_amount:.2f} | Potential: ${potential_profit:.2f}")
        self.log(f"ATR: ${self.atr:.2f} | Trend: {self.current_trend} ({self.trend_strength:.1f}%)")
    
    def go_short(self):
        """Открытие трендовой SHORT позиции"""
        entry_price = self.close
        
        # Стоп-лосс по ATR
        atr_stop = self.atr * self.atr_stop_multiplier
        stop_loss_price = entry_price + atr_stop
        
        # Тейк-профит по соотношению риск/прибыль
        risk_distance = stop_loss_price - entry_price
        take_profit_price = entry_price - (risk_distance * self.profit_target_ratio)
        
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
        
        # Логирование
        risk_amount = qty * risk_distance
        potential_profit = qty * (entry_price - take_profit_price)
        
        self.log(f"=== TREND SHORT #{self.daily_trades_count} ===")
        self.log(f"Reason: {getattr(self, 'entry_reason', 'UNKNOWN')}")
        self.log(f"Size: {qty:.4f} @ ${entry_price:.2f}")
        self.log(f"Stop: ${stop_loss_price:.2f} | Take: ${take_profit_price:.2f}")
        self.log(f"Risk: ${risk_amount:.2f} | Potential: ${potential_profit:.2f}")
        self.log(f"ATR: ${self.atr:.2f} | Trend: {self.current_trend} ({self.trend_strength:.1f}%)")
    
    def update_position(self):
        """Трендовое управление позицией"""
        if not self.position.is_open:
            return
        
        self._analyze_trend()
        
        # Закрываем если тренд изменился
        if self.position_type == 'LONG' and self.current_trend != "BULL":
            self.liquidate()
            self.log(f"🔄 LONG closed: Trend changed to {self.current_trend}")
            self.log(f"P&L: ${self.position.pnl:.2f}")
            self._reset_position()
            return
        
        if self.position_type == 'SHORT' and self.current_trend != "BEAR":
            self.liquidate()
            self.log(f"🔄 SHORT closed: Trend changed to {self.current_trend}")
            self.log(f"P&L: ${self.position.pnl:.2f}")
            self._reset_position()
            return
        
        # Принудительное закрытие по времени
        if self.entry_bar and (self.index - self.entry_bar) >= self.max_holding_hours:
            self.liquidate()
            self.log(f"⏰ Time exit after {self.max_holding_hours} hours")
            self.log(f"P&L: ${self.position.pnl:.2f}")
            self._reset_position()
    
    def _reset_position(self):
        """Сброс переменных позиции"""
        self.entry_bar = None
        self.position_type = None
        if hasattr(self, 'entry_reason'):
            delattr(self, 'entry_reason')
    
    def on_close_position(self, order):
        """Обработка закрытия позиции"""
        pnl = self.position.pnl
        
        # Обновляем счётчик убытков
        if pnl < 0:
            self.consecutive_losses += 1
            self.log(f"❌ Trend Loss: ${pnl:.2f} | Consecutive: {self.consecutive_losses}")
        else:
            self.consecutive_losses = 0
            self.log(f"✅ Trend Profit: ${pnl:.2f} | Reset losses")
        
        self.log(f"🏁 Closed @ ${order.price:.2f} | Daily: {self.daily_trades_count}/{self.max_daily_trades}")
        self._reset_position()
    
    def before(self):
        """Мониторинг тренда каждые 6 часов"""
        if self.index % 6 == 0 and self.index >= self.ema_trend + 20:
            self._analyze_trend()
            
            # Эмодзи для тренда
            trend_emoji = {"BULL": "🚀", "BEAR": "🐻", "NEUTRAL": "😴"}
            
            # Позиция относительно EMA200
            distance_to_trend = (self.close - self.ema200) / self.ema200 * 100
            
            # Объём
            vol_ratio = self.current_volume / self.volume_ma if self.volume_ma > 0 else 1
            vol_emoji = "🔊" if vol_ratio > 2 else "🔉" if vol_ratio > 1.2 else "🔇"
            
            self.log(f"📊 Hour {self.index}: ${self.close:.2f}")
            self.log(f"   Trend: {self.current_trend} {trend_emoji[self.current_trend]} ({self.trend_strength:.1f}%)")
            self.log(f"   EMA200: ${self.ema200:.2f} ({distance_to_trend:+.1f}%)")
            self.log(f"   RSI: {self.rsi:.1f} {vol_emoji} | Trades: {self.daily_trades_count}/2 | L: {self.consecutive_losses}")
            
            if self.position.is_open:
                hours_held = self.index - self.entry_bar if self.entry_bar else 0
                self.log(f"   Position: {self.position_type} {hours_held}h | P&L: ${self.position.pnl:.2f}")
