# strategies/ActiveScalper/__init__.py
from jesse.strategies import Strategy
import jesse.indicators as ta


class ActiveScalper(EnhancedStrategy):
    """
    АКТИВНАЯ СКАЛЬПИНГОВАЯ СТРАТЕГИЯ
    Цель: 5-6 сделок в день на 5-минутном таймфрейме
    Логика: Быстрые EMA кроссоверы + Bollinger Bands + Volume
    """
    
    def __init__(self):
        super().__init__()
        
        # === СКОРОСТНЫЕ ИНДИКАТОРЫ ===
        self.ema_fast = 8           # Быстрая EMA
        self.ema_medium = 13        # Средняя EMA  
        self.ema_slow = 21          # Медленная EMA
        self.bb_period = 20         # Bollinger Bands
        self.bb_std = 2             # Стандартное отклонение BB
        self.volume_ma_period = 10  # Короткий период для объёма
        self.rsi_period = 7         # Быстрый RSI
        
        # === АГРЕССИВНЫЕ УСЛОВИЯ ВХОДА ===
        self.min_volume_ratio = 1.1      # Объём хотя бы 1.1x среднего
        self.candle_body_min = 0.15      # Минимум 0.15% размер свечи
        self.bb_squeeze_threshold = 0.02 # Сжатие BB (<2% от цены)
        
        # === БЫСТРОЕ УПРАВЛЕНИЕ РИСКАМИ ===
        self.risk_percent = 1.5          # Повышен риск для активности
        self.quick_tp_percent = 0.8      # Быстрый ТП 0.8%
        self.quick_sl_percent = 0.5      # Быстрый СЛ 0.5%
        self.scalp_tp_percent = 1.2      # Обычный ТП 1.2%
        self.scalp_sl_percent = 0.8      # Обычный СЛ 0.8%
        self.max_holding_minutes = 120   # Максимум 2 часа (24 свечи по 5 мин)
        
        # === УСЛОВИЯ АКТИВНОСТИ ===
        self.min_gap_minutes = 10        # Минимум 10 минут между сделками (2 свечи)
        self.max_daily_trades = 8        # Максимум 8 сделок в день
        self.max_consecutive_losses = 3   # Пауза после 3 убытков
        
        # === ПЕРЕМЕННЫЕ СОСТОЯНИЯ ===
        self.entry_bar = None
        self.last_trade_bar = None
        self.daily_trades_count = 0
        self.last_day = None
        self.consecutive_losses = 0
        self.position_type = None
        
        self.log(f"=== ACTIVE SCALPER INITIALIZED ===")
        self.log(f"Timeframe: 5m | Target: 5-6 trades/day")
        self.log(f"EMA: {self.ema_fast}/{self.ema_medium}/{self.ema_slow}")
        self.log(f"Risk: {self.risk_percent}% | Quick TP: {self.quick_tp_percent}% | SL: {self.quick_sl_percent}%")

    # === ИНДИКАТОРЫ ===
    @property
    def ema8(self):
        return ta.ema(self.candles, period=self.ema_fast)
    
    @property
    def ema13(self):
        return ta.ema(self.candles, period=self.ema_medium)
    
    @property
    def ema21(self):
        return ta.ema(self.candles, period=self.ema_slow)
    
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
    def volume_ma(self):
        return ta.sma(self.candles[:, 5], period=self.volume_ma_period)
    
    @property
    def rsi_fast(self):
        return ta.rsi(self.candles, period=self.rsi_period)
    
    @property
    def current_volume(self):
        return self.candles[-1, 5]
    
    # === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
    def _update_daily_counter(self):
        """Обновляем счётчик дневных сделок"""
        current_day = self.index // 288  # 288 свечей по 5 мин = 1 день
        if self.last_day != current_day:
            self.daily_trades_count = 0
            self.last_day = current_day
    
    def _is_ema_bullish(self):
        """EMA в бычьем порядке"""
        return self.ema8 > self.ema13 > self.ema21
    
    def _is_ema_bearish(self):
        """EMA в медвежьем порядке"""
        return self.ema8 < self.ema13 < self.ema21
    
    def _is_ema_crossover_bullish(self):
        """Бычий кроссовер EMA8 над EMA13"""
        if self.index < 2:
            return False
        prev_ema8 = ta.ema(self.candles[:-1], period=self.ema_fast)
        prev_ema13 = ta.ema(self.candles[:-1], period=self.ema_medium)
        
        was_below = prev_ema8 <= prev_ema13
        now_above = self.ema8 > self.ema13
        return was_below and now_above
    
    def _is_ema_crossover_bearish(self):
        """Медвежий кроссовер EMA8 под EMA13"""
        if self.index < 2:
            return False
        prev_ema8 = ta.ema(self.candles[:-1], period=self.ema_fast)
        prev_ema13 = ta.ema(self.candles[:-1], period=self.ema_medium)
        
        was_above = prev_ema8 >= prev_ema13
        now_below = self.ema8 < self.ema13
        return was_above and now_below
    
    def _is_bb_squeeze(self):
        """Bollinger Bands сжаты (низкая волатильность)"""
        return self.bb_width < self.bb_squeeze_threshold
    
    def _is_bb_expansion(self):
        """Bollinger Bands расширяются (высокая волатильность)"""
        return self.bb_width > self.bb_squeeze_threshold * 2
    
    def _has_volume_support(self):
        """Есть поддержка объёмом"""
        return self.current_volume > (self.volume_ma * self.min_volume_ratio)
    
    def _is_strong_candle(self):
        """Сильная свеча"""
        body_percent = abs(self.close - self.open) / self.open * 100
        return body_percent >= self.candle_body_min
    
    def _can_trade(self):
        """Базовые условия для торговли"""
        # Обновляем счётчик дня
        self._update_daily_counter()
        
        # Недостаточно данных
        if self.index < max(self.ema_slow, self.bb_period) + 5:
            return False
        
        # Уже есть позиция
        if self.position.is_open:
            return False
        
        # Превышен дневной лимит сделок
        if self.daily_trades_count >= self.max_daily_trades:
            return False
        
        # Слишком много убытков подряд
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False
        
        # Минимальный промежуток между сделками
        if (self.last_trade_bar is not None and 
            (self.index - self.last_trade_bar) < (self.min_gap_minutes // 5)):
            return False
        
        return True

    # === УСЛОВИЯ ВХОДА ===
    def should_long(self) -> bool:
        """
        МНОЖЕСТВЕННЫЕ условия для LONG (для активности):
        
        Сценарий 1: EMA Crossover + Volume
        Сценарий 2: BB Bounce от нижней границы  
        Сценарий 3: BB Breakout вверх
        Сценарий 4: RSI Oversold Recovery
        """
        if not self._can_trade():
            return False
        
        # Базовые фильтры
        volume_ok = self._has_volume_support()
        strong_candle = self._is_strong_candle()
        green_candle = self.close > self.open
        
        # === СЦЕНАРИЙ 1: EMA CROSSOVER ===
        scenario1 = (self._is_ema_crossover_bullish() and 
                    volume_ok and 
                    self.close > self.ema21)
        
        # === СЦЕНАРИЙ 2: BB BOUNCE ===
        scenario2 = (self.close <= self.bb_lower * 1.002 and  # Касание нижней BB
                    green_candle and
                    volume_ok and
                    self._is_ema_bullish())
        
        # === СЦЕНАРИЙ 3: BB BREAKOUT ===  
        scenario3 = (self.close > self.bb_upper and
                    self._is_bb_expansion() and
                    volume_ok and
                    strong_candle)
        
        # === СЦЕНАРИЙ 4: RSI RECOVERY ===
        scenario4 = (self.rsi_fast < 30 and  # Было перепродано
                    self.close > self.open and  # Восстановление
                    volume_ok and
                    self.close > self.ema13)
        
        if scenario1:
            self.log(f"🟢 LONG: EMA Crossover | Price: ${self.close:.2f}")
            self.entry_reason = "EMA_CROSS"
            return True
        elif scenario2:
            self.log(f"🟢 LONG: BB Bounce | Price: ${self.close:.2f}")
            self.entry_reason = "BB_BOUNCE"
            return True
        elif scenario3:
            self.log(f"🟢 LONG: BB Breakout | Price: ${self.close:.2f}")
            self.entry_reason = "BB_BREAKOUT"
            return True
        elif scenario4:
            self.log(f"🟢 LONG: RSI Recovery | Price: ${self.close:.2f}")
            self.entry_reason = "RSI_RECOVERY"
            return True
        
        return False
    
    def should_short(self) -> bool:
        """
        МНОЖЕСТВЕННЫЕ условия для SHORT (для активности):
        
        Сценарий 1: EMA Crossover + Volume
        Сценарий 2: BB Bounce от верхней границы
        Сценарий 3: BB Breakout вниз
        Sценарий 4: RSI Overbought Decline
        """
        if not self._can_trade():
            return False
        
        # Базовые фильтры
        volume_ok = self._has_volume_support()
        strong_candle = self._is_strong_candle()
        red_candle = self.close < self.open
        
        # === СЦЕНАРИЙ 1: EMA CROSSOVER ===
        scenario1 = (self._is_ema_crossover_bearish() and
                    volume_ok and
                    self.close < self.ema21)
        
        # === СЦЕНАРИЙ 2: BB BOUNCE ===
        scenario2 = (self.close >= self.bb_upper * 0.998 and  # Касание верхней BB
                    red_candle and
                    volume_ok and
                    self._is_ema_bearish())
        
        # === СЦЕНАРИЙ 3: BB BREAKOUT ===
        scenario3 = (self.close < self.bb_lower and
                    self._is_bb_expansion() and
                    volume_ok and
                    strong_candle)
        
        # === СЦЕНАРИЙ 4: RSI DECLINE ===
        scenario4 = (self.rsi_fast > 70 and  # Было перекуплено
                    self.close < self.open and  # Снижение
                    volume_ok and
                    self.close < self.ema13)
        
        if scenario1:
            self.log(f"🔴 SHORT: EMA Crossover | Price: ${self.close:.2f}")
            self.entry_reason = "EMA_CROSS"
            return True
        elif scenario2:
            self.log(f"🔴 SHORT: BB Bounce | Price: ${self.close:.2f}")
            self.entry_reason = "BB_BOUNCE"
            return True
        elif scenario3:
            self.log(f"🔴 SHORT: BB Breakout | Price: ${self.close:.2f}")
            self.entry_reason = "BB_BREAKOUT"
            return True
        elif scenario4:
            self.log(f"🔴 SHORT: RSI Decline | Price: ${self.close:.2f}")
            self.entry_reason = "RSI_DECLINE"
            return True
        
        return False
    
    def should_cancel_entry(self) -> bool:
        return False
    
    # === УПРАВЛЕНИЕ ПОЗИЦИЯМИ ===
    def _calculate_position_size(self, entry_price, stop_loss_price):
        """Расчёт размера позиции"""
        risk_amount = self.available_margin * (self.risk_percent / 100)
        price_diff = abs(entry_price - stop_loss_price)
        
        if price_diff > 0:
            qty = risk_amount / price_diff
            max_qty = (self.available_margin * 0.9) / entry_price
            return min(qty, max_qty, 0.5)  # Максимум 0.5 BTC
        else:
            return 0.001
    
    def go_long(self):
        """Открытие LONG позиции с адаптивными уровнями"""
        entry_price = self.close
        
        # Выбираем уровни в зависимости от причины входа
        if hasattr(self, 'entry_reason'):
            if self.entry_reason in ['BB_BREAKOUT', 'EMA_CROSS']:
                # Более агрессивные уровни для breakout
                tp_percent = self.scalp_tp_percent
                sl_percent = self.scalp_sl_percent
            else:
                # Быстрые уровни для bounce/recovery  
                tp_percent = self.quick_tp_percent
                sl_percent = self.quick_sl_percent
        else:
            tp_percent = self.quick_tp_percent
            sl_percent = self.quick_sl_percent
        
        stop_loss_price = entry_price * (1 - sl_percent / 100)
        take_profit_price = entry_price * (1 + tp_percent / 100)
        
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
        
        self.log(f"=== LONG #{self.daily_trades_count} ===")
        self.log(f"Reason: {getattr(self, 'entry_reason', 'UNKNOWN')}")
        self.log(f"Size: {qty:.4f} @ ${entry_price:.2f}")
        self.log(f"SL: ${stop_loss_price:.2f} (-{sl_percent}%)")
        self.log(f"TP: ${take_profit_price:.2f} (+{tp_percent}%)")
        self.log(f"Vol: {self.current_volume/self.volume_ma:.1f}x | RSI: {self.rsi_fast:.1f}")
    
    def go_short(self):
        """Открытие SHORT позиции с адаптивными уровнями"""
        entry_price = self.close
        
        # Выбираем уровни в зависимости от причины входа
        if hasattr(self, 'entry_reason'):
            if self.entry_reason in ['BB_BREAKOUT', 'EMA_CROSS']:
                tp_percent = self.scalp_tp_percent
                sl_percent = self.scalp_sl_percent
            else:
                tp_percent = self.quick_tp_percent
                sl_percent = self.quick_sl_percent
        else:
            tp_percent = self.quick_tp_percent
            sl_percent = self.quick_sl_percent
        
        stop_loss_price = entry_price * (1 + sl_percent / 100)
        take_profit_price = entry_price * (1 - tp_percent / 100)
        
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
        
        self.log(f"=== SHORT #{self.daily_trades_count} ===")
        self.log(f"Reason: {getattr(self, 'entry_reason', 'UNKNOWN')}")
        self.log(f"Size: {qty:.4f} @ ${entry_price:.2f}")
        self.log(f"SL: ${stop_loss_price:.2f} (+{sl_percent}%)")
        self.log(f"TP: ${take_profit_price:.2f} (-{tp_percent}%)")
        self.log(f"Vol: {self.current_volume/self.volume_ma:.1f}x | RSI: {self.rsi_fast:.1f}")
    
    def update_position(self):
        """Управление открытой позицией"""
        if not self.position.is_open:
            return
        
        # Принудительное закрытие по времени (скальпинг = быстро)
        if self.entry_bar and (self.index - self.entry_bar) >= (self.max_holding_minutes // 5):
            self.liquidate()
            self.log(f"⏰ Time exit after {self.max_holding_minutes} min")
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
            self.log(f"❌ Loss: ${pnl:.2f} | Consecutive: {self.consecutive_losses}")
        else:
            self.consecutive_losses = 0
            self.log(f"✅ Profit: ${pnl:.2f} | Reset losses")
        
        self.log(f"🔚 Closed @ ${order.price:.2f} | Daily trades: {self.daily_trades_count}")
        self._reset_position()
    
    def before(self):
        """Мониторинг каждые 2 часа (24 свечи по 5 мин)"""
        if self.index % 24 == 0 and self.index >= self.bb_period:
            self._update_daily_counter()
            
            # Анализ рынка
            ema_trend = "📈" if self._is_ema_bullish() else "📉" if self._is_ema_bearish() else "↔️"
            bb_state = "🟰" if self._is_bb_squeeze() else "📊" if self._is_bb_expansion() else "⚪"
            vol_state = "🔊" if self.current_volume > self.volume_ma * 1.5 else "🔉"
            
            self.log(f"📊 {self.index//24*2}h: ${self.close:.2f}")
            self.log(f"   {ema_trend} RSI:{self.rsi_fast:.0f} {bb_state} {vol_state}")
            self.log(f"   Daily trades: {self.daily_trades_count}/8 | Losses: {self.consecutive_losses}")
            
            if self.position.is_open:
                minutes_held = (self.index - self.entry_bar) * 5 if self.entry_bar else 0
                self.log(f"   Position: {self.position_type} {minutes_held}min | P&L: ${self.position.pnl:.2f}")
