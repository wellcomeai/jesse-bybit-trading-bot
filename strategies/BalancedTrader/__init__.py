# strategies/BalancedTrader/__init__.py
from jesse.strategies import Strategy
import jesse.indicators as ta


class BalancedTrader(Strategy):
    """
    BALANCED TRADER v2.0 - Улучшенная золотая середина
    Цель: 3-5 сделок в неделю с винрейтом 55-65%
    Таймфрейм: 15 минут (компромисс между активностью и качеством)
    
    Улучшения v2.0:
    - Исправлен конфликт сигналов (ConflictingRules)
    - Добавлены дополнительные фильтры качества
    - Улучшена логика взаимоисключения long/short
    - Добавлена защита от ложных сигналов
    """
    
    def __init__(self):
        super().__init__()
        
        # === СБАЛАНСИРОВАННЫЕ ИНДИКАТОРЫ ===
        self.ema_fast = 9           # Быстрая EMA
        self.ema_slow = 21          # Медленная EMA
        self.rsi_period = 14        # Стандартный RSI
        self.bb_period = 20         # Bollinger Bands
        self.bb_std = 2             # Стандартное отклонение
        self.volume_ma_period = 14  # Объём
        self.atr_period = 14        # ATR
        
        # === УЛУЧШЕННЫЕ УСЛОВИЯ ВХОДА ===
        self.rsi_oversold = 30      # Более строгая перепроданность
        self.rsi_overbought = 70    # Более строгая перекупленность
        self.rsi_neutral_min = 40   # Нижняя граница нейтральной зоны
        self.rsi_neutral_max = 60   # Верхняя граница нейтральной зоны
        self.min_volume_ratio = 1.3 # Объём 1.3x среднего (строже)
        self.min_candle_body = 0.25 # Минимум 0.25% размер свечи
        self.trend_strength_min = 0.4 # Увеличенная сила тренда
        
        # === СБАЛАНСИРОВАННЫЕ РИСКИ ===
        self.risk_percent = 1.0     # 1% риск на сделку
        self.stop_loss_atr = 1.8    # 1.8x ATR для стопа
        self.take_profit_atr = 3.6  # 3.6x ATR для профита (1:2 R:R)
        self.max_holding_bars = 32  # Максимум 8 часов (32 свечи по 15 мин)
        
        # === АКТИВНОСТЬ ===
        self.max_daily_trades = 3   # Снижено до 3 для качества
        self.min_gap_bars = 6       # Увеличено до 1.5 часа между сделками
        self.max_consecutive_losses = 3 # Пауза после 3 убытков
        
        # === НОВЫЕ ФИЛЬТРЫ КАЧЕСТВА ===
        self.min_ema_separation = 0.2  # Минимальное расстояние между EMA в %
        self.bb_squeeze_threshold = 1.5 # Минимальная ширина BB в %
        self.volume_spike_threshold = 2.0 # Порог всплеска объёма
        
        # === ПЕРЕМЕННЫЕ СОСТОЯНИЯ ===
        self.entry_bar = None
        self.position_type = None
        self.daily_trades_count = 0
        self.last_day = None
        self.last_trade_bar = None
        self.consecutive_losses = 0
        
        # === НОВЫЕ ПЕРЕМЕННЫЕ ===
        self.signal_strength = 0    # Сила последнего сигнала (0-10)
        self.market_regime = "NEUTRAL" # BULL, BEAR, NEUTRAL
        
        self.log(f"=== BALANCED TRADER v2.0 INITIALIZED ===")
        self.log(f"Target: 3-5 trades per week (Improved Quality)")
        self.log(f"Timeframe: 15m | Risk: {self.risk_percent}% | R:R = 1:2")
        self.log(f"Max daily trades: {self.max_daily_trades} (Quality > Quantity)")

    # === ИНДИКАТОРЫ ===
    @property
    def ema9(self):
        return ta.ema(self.candles, period=self.ema_fast)
    
    @property
    def ema21(self):
        return ta.ema(self.candles, period=self.ema_slow)
    
    @property
    def rsi(self):
        return ta.rsi(self.candles, period=self.rsi_period)
    
    @property
    def bb_upper(self):
        return ta.bollinger_bands(self.candles, period=self.bb_period, devup=self.bb_std)[0]
    
    @property
    def bb_middle(self):
        return ta.bollinger_bands(self.candles, period=self.bb_period, devup=self.bb_std)[1]
    
    @property
    def bb_lower(self):
        return ta.bollinger_bands(self.candles, period=self.bb_period, devup=self.bb_std)[2]
    
    @property
    def bb_width(self):
        """Ширина Bollinger Bands в % от цены"""
        return ((self.bb_upper - self.bb_lower) / self.bb_middle) * 100
    
    @property
    def atr(self):
        return ta.atr(self.candles, period=self.atr_period)
    
    @property
    def volume_ma(self):
        return ta.sma(self.candles[:, 5], period=self.volume_ma_period)
    
    @property
    def current_volume(self):
        return self.candles[-1, 5]
    
    # === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
    def _update_daily_counter(self):
        """Обновляем счётчик дневных сделок"""
        current_day = self.index // 96  # 96 свечей по 15 мин = 1 день
        if self.last_day != current_day:
            if self.daily_trades_count > 0:
                self.log(f"📅 Day {current_day}: Had {self.daily_trades_count} trades yesterday")
            self.daily_trades_count = 0
            self.last_day = current_day
    
    def _update_market_regime(self):
        """Определяем режим рынка"""
        if self.index < 48:  # Нужно минимум 2 дня данных
            return
        
        # Анализ за последние 2 дня (48 свечей)
        price_48h_ago = self.candles[-48, 4]  # Цена закрытия 48 свечей назад
        price_change = (self.close - price_48h_ago) / price_48h_ago * 100
        
        if price_change > 3:
            self.market_regime = "BULL"
        elif price_change < -3:
            self.market_regime = "BEAR"
        else:
            self.market_regime = "NEUTRAL"
    
    def _get_ema_separation(self):
        """Расстояние между EMA в процентах"""
        return abs(self.ema9 - self.ema21) / self.ema21 * 100
    
    def _is_trending_up(self):
        """Улучшенная проверка восходящего тренда"""
        price_above_ema = self.close > self.ema21
        ema_trending_up = self.ema9 > self.ema21
        
        # Проверяем силу тренда
        trend_strength = (self.close - self.ema21) / self.ema21 * 100
        strong_enough = trend_strength > self.trend_strength_min
        
        # Проверяем разделение EMA
        ema_separation = self._get_ema_separation()
        good_separation = ema_separation > self.min_ema_separation
        
        return price_above_ema and ema_trending_up and strong_enough and good_separation
    
    def _is_trending_down(self):
        """Улучшенная проверка нисходящего тренда"""
        price_below_ema = self.close < self.ema21
        ema_trending_down = self.ema9 < self.ema21
        
        # Проверяем силу тренда
        trend_strength = (self.ema21 - self.close) / self.ema21 * 100
        strong_enough = trend_strength > self.trend_strength_min
        
        # Проверяем разделение EMA
        ema_separation = self._get_ema_separation()
        good_separation = ema_separation > self.min_ema_separation
        
        return price_below_ema and ema_trending_down and strong_enough and good_separation
    
    def _has_volume_support(self):
        """Улучшенная проверка поддержки объёмом"""
        base_volume = self.current_volume > (self.volume_ma * self.min_volume_ratio)
        
        # Дополнительно проверяем всплеск объёма
        volume_spike = self.current_volume > (self.volume_ma * self.volume_spike_threshold)
        
        return base_volume or volume_spike
    
    def _is_good_candle(self):
        """Улучшенная проверка качества свечи"""
        body_percent = abs(self.close - self.open) / self.open * 100
        body_ok = body_percent >= self.min_candle_body
        
        # Проверяем, что свеча не является доджи (слишком маленькое тело)
        body_vs_range = abs(self.close - self.open) / (self.high - self.low)
        not_doji = body_vs_range > 0.3  # Тело должно быть минимум 30% от диапазона
        
        return body_ok and not_doji
    
    def _bb_not_squeezed(self):
        """Проверяем, что Bollinger Bands не сжаты"""
        return self.bb_width > self.bb_squeeze_threshold
    
    def _near_bb_support(self):
        """Цена около нижней границы BB"""
        distance_to_lower = (self.close - self.bb_lower) / self.close * 100
        return distance_to_lower < 0.5
    
    def _near_bb_resistance(self):
        """Цена около верхней границы BB"""
        distance_to_upper = (self.bb_upper - self.close) / self.close * 100
        return distance_to_upper < 0.5
    
    def _can_trade(self):
        """Базовые условия для торговли"""
        self._update_daily_counter()
        self._update_market_regime()
        
        # Недостаточно данных
        if self.index < max(self.ema_slow, self.bb_period, self.volume_ma_period, 48) + 10:
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
            (self.index - self.last_trade_bar) < self.min_gap_bars):
            return False
        
        # BB не должны быть сжаты (низкая волатильность)
        if not self._bb_not_squeezed():
            return False
        
        return True
    
    def _calculate_signal_strength_long(self):
        """Рассчитываем силу LONG сигнала (0-10)"""
        strength = 0
        
        # Тренд (0-3 баллов)
        if self._is_trending_up():
            strength += 3
        elif self.close > self.ema9 > self.ema21:
            strength += 1
        
        # RSI (0-2 балла)
        if self.rsi < self.rsi_neutral_min:
            strength += 2
        elif self.rsi < 50:
            strength += 1
        
        # Объём (0-2 балла)
        vol_ratio = self.current_volume / self.volume_ma if self.volume_ma > 0 else 1
        if vol_ratio > self.volume_spike_threshold:
            strength += 2
        elif vol_ratio > self.min_volume_ratio:
            strength += 1
        
        # Свеча (0-2 балла)
        if self._is_good_candle() and self.close > self.open:
            strength += 2
        
        # BB позиция (0-1 балл)
        if self._near_bb_support():
            strength += 1
        
        return strength
    
    def _calculate_signal_strength_short(self):
        """Рассчитываем силу SHORT сигнала (0-10)"""
        strength = 0
        
        # Тренд (0-3 баллов)
        if self._is_trending_down():
            strength += 3
        elif self.close < self.ema9 < self.ema21:
            strength += 1
        
        # RSI (0-2 балла)
        if self.rsi > self.rsi_neutral_max:
            strength += 2
        elif self.rsi > 50:
            strength += 1
        
        # Объём (0-2 балла)
        vol_ratio = self.current_volume / self.volume_ma if self.volume_ma > 0 else 1
        if vol_ratio > self.volume_spike_threshold:
            strength += 2
        elif vol_ratio > self.min_volume_ratio:
            strength += 1
        
        # Свеча (0-2 балла)
        if self._is_good_candle() and self.close < self.open:
            strength += 2
        
        # BB позиция (0-1 балл)
        if self._near_bb_resistance():
            strength += 1
        
        return strength

    # === УЛУЧШЕННЫЕ УСЛОВИЯ ВХОДА С ЗАЩИТОЙ ОТ КОНФЛИКТОВ ===
    def should_long(self) -> bool:
        """
        УЛУЧШЕННЫЕ условия для LONG с защитой от конфликтов:
        
        1. Базовые проверки
        2. Расчёт силы сигнала
        3. Минимальная сила сигнала = 6/10
        4. Взаимоисключение с SHORT сигналами
        """
        if not self._can_trade():
            return False
        
        # Рассчитываем силу сигналов
        long_strength = self._calculate_signal_strength_long()
        short_strength = self._calculate_signal_strength_short()
        
        # КРИТИЧЕСКИ ВАЖНО: взаимоисключение
        # LONG возможен только если его сила значительно больше SHORT
        if short_strength >= long_strength:
            return False
        
        # Минимальная разница в силе сигналов
        if (long_strength - short_strength) < 2:
            return False
        
        # Минимальная сила LONG сигнала
        if long_strength < 6:
            return False
        
        # Дополнительные фильтры
        rsi_allows_long = self.rsi < self.rsi_overbought
        market_allows = self.market_regime in ["BULL", "NEUTRAL"]
        
        # Итоговое решение
        if rsi_allows_long and market_allows:
            self.signal_strength = long_strength
            self.log(f"🟢 LONG: Strength {long_strength}/10 vs SHORT {short_strength}/10")
            self.log(f"   Price: ${self.close:.2f} | RSI: {self.rsi:.1f} | Market: {self.market_regime}")
            self.entry_reason = f"STRENGTH_{long_strength}"
            return True
        
        return False
    
    def should_short(self) -> bool:
        """
        УЛУЧШЕННЫЕ условия для SHORT с защитой от конфликтов:
        
        1. Базовые проверки
        2. Расчёт силы сигнала
        3. Минимальная сила сигнала = 6/10
        4. Взаимоисключение с LONG сигналами
        """
        if not self._can_trade():
            return False
        
        # Рассчитываем силу сигналов
        long_strength = self._calculate_signal_strength_long()
        short_strength = self._calculate_signal_strength_short()
        
        # КРИТИЧЕСКИ ВАЖНО: взаимоисключение
        # SHORT возможен только если его сила значительно больше LONG
        if long_strength >= short_strength:
            return False
        
        # Минимальная разница в силе сигналов
        if (short_strength - long_strength) < 2:
            return False
        
        # Минимальная сила SHORT сигнала
        if short_strength < 6:
            return False
        
        # Дополнительные фильтры
        rsi_allows_short = self.rsi > self.rsi_oversold
        market_allows = self.market_regime in ["BEAR", "NEUTRAL"]
        
        # Итоговое решение
        if rsi_allows_short and market_allows:
            self.signal_strength = short_strength
            self.log(f"🔴 SHORT: Strength {short_strength}/10 vs LONG {long_strength}/10")
            self.log(f"   Price: ${self.close:.2f} | RSI: {self.rsi:.1f} | Market: {self.market_regime}")
            self.entry_reason = f"STRENGTH_{short_strength}"
            return True
        
        return False
    
    def should_cancel_entry(self) -> bool:
        return False
    
    # === УЛУЧШЕННОЕ УПРАВЛЕНИЕ ПОЗИЦИЯМИ ===
    def _calculate_position_size(self, entry_price, stop_loss_price):
        """Улучшенный расчёт размера позиции"""
        risk_amount = self.available_margin * (self.risk_percent / 100)
        price_diff = abs(entry_price - stop_loss_price)
        
        if price_diff > 0:
            qty = risk_amount / price_diff
            
            # Адаптивное ограничение на основе силы сигнала
            strength_multiplier = min(self.signal_strength / 10.0, 0.8)
            max_qty = (self.available_margin * strength_multiplier) / entry_price
            
            return min(qty, max_qty, 0.15)  # Максимум 0.15 BTC
        else:
            return 0.001
    
    def go_long(self):
        """Открытие улучшенной LONG позиции"""
        entry_price = self.close
        
        # Адаптивный стоп-лосс (сильнее сигнал = ближе стоп)
        atr_value = self.atr
        stop_multiplier = self.stop_loss_atr * (10 - self.signal_strength) / 10
        stop_loss_price = entry_price - (atr_value * stop_multiplier)
        take_profit_price = entry_price + (atr_value * self.take_profit_atr)
        
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
        
        # Улучшенное логирование
        risk_amount = qty * (entry_price - stop_loss_price)
        potential_profit = qty * (take_profit_price - entry_price)
        
        self.log(f"=== BALANCED LONG #{self.daily_trades_count} (v2.0) ===")
        self.log(f"Reason: {getattr(self, 'entry_reason', 'UNKNOWN')}")
        self.log(f"Size: {qty:.4f} @ ${entry_price:.2f}")
        self.log(f"SL: ${stop_loss_price:.2f} | TP: ${take_profit_price:.2f}")
        self.log(f"Risk: ${risk_amount:.2f} | Potential: ${potential_profit:.2f}")
        self.log(f"Signal Strength: {self.signal_strength}/10")
        self.log(f"RSI: {self.rsi:.1f} | Vol: {self.current_volume/self.volume_ma:.1f}x | BB: {self.bb_width:.1f}%")
    
    def go_short(self):
        """Открытие улучшенной SHORT позиции"""
        entry_price = self.close
        
        # Адаптивный стоп-лосс
        atr_value = self.atr
        stop_multiplier = self.stop_loss_atr * (10 - self.signal_strength) / 10
        stop_loss_price = entry_price + (atr_value * stop_multiplier)
        take_profit_price = entry_price - (atr_value * self.take_profit_atr)
        
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
        
        # Улучшенное логирование
        risk_amount = qty * (stop_loss_price - entry_price)
        potential_profit = qty * (entry_price - take_profit_price)
        
        self.log(f"=== BALANCED SHORT #{self.daily_trades_count} (v2.0) ===")
        self.log(f"Reason: {getattr(self, 'entry_reason', 'UNKNOWN')}")
        self.log(f"Size: {qty:.4f} @ ${entry_price:.2f}")
        self.log(f"SL: ${stop_loss_price:.2f} | TP: ${take_profit_price:.2f}")
        self.log(f"Risk: ${risk_amount:.2f} | Potential: ${potential_profit:.2f}")
        self.log(f"Signal Strength: {self.signal_strength}/10")
        self.log(f"RSI: {self.rsi:.1f} | Vol: {self.current_volume/self.volume_ma:.1f}x | BB: {self.bb_width:.1f}%")
    
    def update_position(self):
        """Улучшенное управление позицией"""
        if not self.position.is_open:
            return
        
        # Принудительное закрытие по времени
        if self.entry_bar and (self.index - self.entry_bar) >= self.max_holding_bars:
            self.liquidate()
            self.log(f"⏰ Time exit after {self.max_holding_bars*15} minutes")
            self.log(f"P&L: ${self.position.pnl:.2f}")
            self._reset_position()
        
        # Адаптивный выход по изменению условий (новое!)
        if self.entry_bar and (self.index - self.entry_bar) >= 8:  # Минимум 2 часа в позиции
            current_long_strength = self._calculate_signal_strength_long()
            current_short_strength = self._calculate_signal_strength_short()
            
            # Если сигнал развернулся - выходим
            if self.position_type == 'LONG' and current_short_strength > current_long_strength + 3:
                self.liquidate()
                self.log(f"🔄 Long exit: Signal reversed (SHORT {current_short_strength} > LONG {current_long_strength})")
                self.log(f"P&L: ${self.position.pnl:.2f}")
                self._reset_position()
            elif self.position_type == 'SHORT' and current_long_strength > current_short_strength + 3:
                self.liquidate()
                self.log(f"🔄 Short exit: Signal reversed (LONG {current_long_strength} > SHORT {current_short_strength})")
                self.log(f"P&L: ${self.position.pnl:.2f}")
                self._reset_position()
    
    def _reset_position(self):
        """Сброс переменных позиции"""
        self.entry_bar = None
        self.position_type = None
        self.signal_strength = 0
        if hasattr(self, 'entry_reason'):
            delattr(self, 'entry_reason')
    
    def on_close_position(self, order):
        """Улучшенная обработка закрытия позиции"""
        pnl = self.position.pnl
        
        # Обновляем счётчик убытков с анализом
        if pnl < 0:
            self.consecutive_losses += 1
            loss_percent = (pnl / self.available_margin) * 100
            self.log(f"❌ Loss: ${pnl:.2f} ({loss_percent:.2f}%) | Consecutive: {self.consecutive_losses}")
            
            # Адаптация после убытков
            if self.consecutive_losses == 2:
                self.log("⚠️ 2 losses - increasing caution (higher signal strength required)")
            elif self.consecutive_losses >= 3:
                self.log("🛑 3+ losses - maximum caution mode")
        else:
            self.consecutive_losses = 0
            profit_percent = (pnl / self.available_margin) * 100
            self.log(f"✅ Profit: ${pnl:.2f} ({profit_percent:.2f}%) | Reset losses")
        
        self.log(f"🔚 Closed @ ${order.price:.2f} | Daily: {self.daily_trades_count}/{self.max_daily_trades}")
        self._reset_position()
    
    def before(self):
        """Улучшенный мониторинг каждые 3 часа"""
        if self.index % 12 == 0 and self.index >= max(self.bb_period, 48):
            self._update_daily_counter()
            self._update_market_regime()
            
            # Расчёт текущих сил сигналов
            long_str = self._calculate_signal_strength_long()
            short_str = self._calculate_signal_strength_short()
            
            # Состояние рынка
            trend_emoji = "📈" if self._is_trending_up() else "📉" if self._is_trending_down() else "↔️"
            
            vol_ratio = self.current_volume / self.volume_ma if self.volume_ma > 0 else 1
            vol_emoji = "🔊" if vol_ratio > 2 else "🔉" if vol_ratio > 1.3 else "🔇"
            
            self.log(f"📊 {(self.index*15)//60}h: ${self.close:.2f} | {self.market_regime}")
            self.log(f"   {trend_emoji} RSI:{self.rsi:.0f} {vol_emoji} BB:{self.bb_width:.1f}%")
            self.log(f"   Signals: 🟢{long_str} 🔴{short_str} | Trades: {self.daily_trades_count}/3 | L: {self.consecutive_losses}")
            
            if self.position.is_open:
                minutes_held = (self.index - self.entry_bar) * 15 if self.entry_bar else 0
                self.log(f"   Position: {self.position_type} {minutes_held//60}h{minutes_held%60}m | P&L: ${self.position.pnl:.2f}")
