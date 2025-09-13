# strategies/FakeoutHunter/__init__.py
from jesse.strategies import Strategy
import jesse.indicators as ta
import numpy as np


class FakeoutHunter(Strategy):
    """
    FAKEOUT HUNTER v3.0 - Активная версия
    
    Философия: Больше сигналов, сохраняем качество
    Логика: Ложные пробои + отскоки от BB + EMA отскоки
    
    Улучшения v3.0:
    1. Добавлены обычные отскоки от BB (не только фейки)
    2. EMA отскоки как дополнительные сигналы
    3. Еще более мягкие условия
    4. Баланс между лонгами и шортами
    """
    
    def __init__(self):
        super().__init__()
        
        # === ИНДИКАТОРЫ ===
        self.bb_period = 20             # Bollinger Bands
        self.bb_std = 2.0               # Стандартное отклонение
        self.ema_period = 50            # EMA как уровень
        self.rsi_period = 14            # RSI для фильтрации
        self.atr_period = 14            # ATR для стопов
        self.volume_ma_period = 20      # Объем
        
        # === ЛОЖНЫЕ ПРОБОИ (оригинальные) ===
        self.max_fakeout_penetration = 0.4    # Увеличено до 0.4%
        self.min_fakeout_return = 0.05        # Уменьшено до 0.05%
        self.max_bars_outside = 4             # Увеличено до 4 свечей
        
        # === НОВЫЕ ТИПЫ СИГНАЛОВ ===
        self.enable_bb_bounces = True         # Обычные отскоки от BB
        self.enable_ema_bounces = True        # Отскоки от EMA
        self.bb_bounce_tolerance = 0.2        # Касание BB в пределах 0.2%
        self.ema_bounce_tolerance = 0.3       # Касание EMA в пределах 0.3%
        
        # === МЯГКИЕ УСЛОВИЯ ===
        self.min_bb_width = 0.8               # Еще меньше (было 1.0)
        self.rsi_overbought = 85              # Очень мягко (было 75)
        self.rsi_oversold = 15                # Очень мягко (было 25)
        self.min_volume_ratio = 0.6           # Еще мягче (было 0.8)
        self.require_ema_confluence = False   # Убираем обязательность
        
        # === УПРАВЛЕНИЕ РИСКАМИ ===
        self.risk_percent = 1.8               # Увеличиваем риск
        self.atr_stop_multiplier = 1.8        # Ближе стоп
        self.profit_target_atr = 2.5          # Ближе цель
        self.max_holding_bars = 20            # 5 часов максимум
        
        # === АКТИВНОСТЬ ===
        self.max_daily_trades = 8             # Еще больше (было 6)
        self.min_gap_bars = 2                 # Всего 30 минут (было 4)
        self.max_consecutive_losses = 5       # Больше терпения
        
        # === БАЛАНСИРОВКА ===
        self.force_balance_trades = True      # Принудительный баланс
        self.max_direction_imbalance = 0.7    # Максимум 70% в одну сторону
        
        # === СОСТОЯНИЕ ===
        self.entry_bar = None
        self.position_type = None
        self.daily_trades_count = 0
        self.last_day = None
        self.last_trade_bar = None
        self.consecutive_losses = 0
        
        # === СЧЕТЧИКИ НАПРАВЛЕНИЙ ===
        self.total_longs = 0
        self.total_shorts = 0
        
        self.log(f"=== FAKEOUT HUNTER v3.0 (Active) ===")
        self.log(f"Multiple signal types: Fakeouts + BB Bounces + EMA Bounces")
        self.log(f"Risk: {self.risk_percent}% | Max trades: {self.max_daily_trades}")
        self.log(f"Balance enforcement: {self.force_balance_trades}")

    # === ИНДИКАТОРЫ ===
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
        return ((self.bb_upper - self.bb_lower) / self.bb_middle) * 100
    
    @property
    def ema50(self):
        return ta.ema(self.candles, period=self.ema_period)
    
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
    
    # === ЛОЖНЫЕ ПРОБОИ (ОРИГИНАЛ) ===
    def _is_bb_lower_fakeout(self):
        """Ложный пробой нижней границы BB"""
        for i in range(1, self.max_bars_outside + 1):
            if self.index < i:
                continue
            
            past_low = self.candles[-i, 3]
            bb_lower_then = ta.bollinger_bands(self.candles[:-i] if i > 0 else self.candles, 
                                              period=self.bb_period, devup=self.bb_std)[2]
            
            penetration = (bb_lower_then - past_low) / bb_lower_then * 100
            
            if 0 < penetration <= self.max_fakeout_penetration:
                return_distance = (self.close - self.bb_lower) / self.bb_lower * 100
                if return_distance >= self.min_fakeout_return:
                    return True, "FAKEOUT"
        return False, None
    
    def _is_bb_upper_fakeout(self):
        """Ложный пробой верхней границы BB"""
        for i in range(1, self.max_bars_outside + 1):
            if self.index < i:
                continue
            
            past_high = self.candles[-i, 2]
            bb_upper_then = ta.bollinger_bands(self.candles[:-i] if i > 0 else self.candles, 
                                              period=self.bb_period, devup=self.bb_std)[0]
            
            penetration = (past_high - bb_upper_then) / bb_upper_then * 100
            
            if 0 < penetration <= self.max_fakeout_penetration:
                return_distance = (self.bb_upper - self.close) / self.bb_upper * 100
                if return_distance >= self.min_fakeout_return:
                    return True, "FAKEOUT"
        return False, None
    
    # === НОВЫЕ СИГНАЛЫ: ОТСКОКИ ===
    def _is_bb_lower_bounce(self):
        """Отскок от нижней границы BB"""
        if not self.enable_bb_bounces:
            return False, None
        
        # Проверяем касание нижней границы
        distance_to_lower = abs(self.close - self.bb_lower) / self.bb_lower * 100
        
        if distance_to_lower <= self.bb_bounce_tolerance:
            # Проверяем, была ли свеча ниже или касалась
            low_touched = self.low <= self.bb_lower * (1 + self.bb_bounce_tolerance / 100)
            green_candle = self.close > self.open
            
            if low_touched and green_candle:
                return True, "BB_BOUNCE"
        
        return False, None
    
    def _is_bb_upper_bounce(self):
        """Отскок от верхней границы BB"""
        if not self.enable_bb_bounces:
            return False, None
        
        # Проверяем касание верхней границы
        distance_to_upper = abs(self.close - self.bb_upper) / self.bb_upper * 100
        
        if distance_to_upper <= self.bb_bounce_tolerance:
            # Проверяем, была ли свеча выше или касалась
            high_touched = self.high >= self.bb_upper * (1 - self.bb_bounce_tolerance / 100)
            red_candle = self.close < self.open
            
            if high_touched and red_candle:
                return True, "BB_BOUNCE"
        
        return False, None
    
    def _is_ema_bounce_up(self):
        """Отскок вверх от EMA"""
        if not self.enable_ema_bounces:
            return False, None
        
        distance_to_ema = abs(self.close - self.ema50) / self.ema50 * 100
        
        if distance_to_ema <= self.ema_bounce_tolerance:
            # EMA поддержка: цена была около или ниже EMA, теперь выше
            low_near_ema = self.low <= self.ema50 * (1 + self.ema_bounce_tolerance / 100)
            close_above_ema = self.close > self.ema50
            green_candle = self.close > self.open
            
            if low_near_ema and close_above_ema and green_candle:
                return True, "EMA_BOUNCE"
        
        return False, None
    
    def _is_ema_bounce_down(self):
        """Отскок вниз от EMA"""
        if not self.enable_ema_bounces:
            return False, None
        
        distance_to_ema = abs(self.close - self.ema50) / self.ema50 * 100
        
        if distance_to_ema <= self.ema_bounce_tolerance:
            # EMA сопротивление: цена была около или выше EMA, теперь ниже
            high_near_ema = self.high >= self.ema50 * (1 - self.ema_bounce_tolerance / 100)
            close_below_ema = self.close < self.ema50
            red_candle = self.close < self.open
            
            if high_near_ema and close_below_ema and red_candle:
                return True, "EMA_BOUNCE"
        
        return False, None
    
    # === БАЛАНСИРОВКА ===
    def _should_prefer_direction(self, direction):
        """Проверяем, нужно ли предпочесть определенное направление"""
        if not self.force_balance_trades:
            return True
        
        total_trades = self.total_longs + self.total_shorts
        if total_trades < 10:  # Первые 10 сделок без ограничений
            return True
        
        if direction == "long":
            long_ratio = self.total_longs / total_trades
            return long_ratio < self.max_direction_imbalance
        else:
            short_ratio = self.total_shorts / total_trades
            return short_ratio < self.max_direction_imbalance
    
    def _update_daily_counter(self):
        """Обновляем счётчик дневных сделок"""
        current_day = self.index // 96
        if self.last_day != current_day:
            if self.daily_trades_count > 0:
                long_pct = (self.total_longs / (self.total_longs + self.total_shorts) * 100) if (self.total_longs + self.total_shorts) > 0 else 50
                self.log(f"📅 Day {current_day}: {self.daily_trades_count} trades | Balance: {long_pct:.0f}% longs")
            self.daily_trades_count = 0
            self.last_day = current_day
    
    def _can_trade(self):
        """Условия для торговли"""
        self._update_daily_counter()
        
        # Недостаточно данных
        if self.index < max(self.bb_period, self.ema_period, self.volume_ma_period) + 5:
            return False
        
        # BB слишком сжаты
        if self.bb_width < self.min_bb_width:
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
        
        # Объем (очень мягко)
        vol_ratio = self.current_volume / self.volume_ma if self.volume_ma > 0 else 1
        if vol_ratio < self.min_volume_ratio:
            return False
        
        return True

    # === ВЗАИМОИСКЛЮЧАЮЩИЕ ПРОВЕРКИ ===
    def _would_long(self):
        """Проверяем потенциал LONG сигналов БЕЗ выполнения условий торговли"""
        try:
            # RSI фильтр
            if self.rsi > self.rsi_overbought:
                return False
            
            # Проверяем сигналы
            bb_fakeout, _ = self._is_bb_lower_fakeout()
            bb_bounce, _ = self._is_bb_lower_bounce()  
            ema_bounce, _ = self._is_ema_bounce_up()
            
            return bb_fakeout or bb_bounce or ema_bounce
        except:
            return False
    
    def _would_short(self):
        """Проверяем потенциал SHORT сигналов БЕЗ выполнения условий торговли"""
        try:
            # RSI фильтр
            if self.rsi < self.rsi_oversold:
                return False
            
            # Проверяем сигналы
            bb_fakeout, _ = self._is_bb_upper_fakeout()
            bb_bounce, _ = self._is_bb_upper_bounce()
            ema_bounce, _ = self._is_ema_bounce_down()
            
            return bb_fakeout or bb_bounce or ema_bounce
        except:
            return False

    # === АКТИВНЫЕ УСЛОВИЯ ВХОДА ===
    def should_long(self) -> bool:
        """
        Множественные условия для LONG:
        1. Ложный пробой BB нижней границы
        2. Отскок от BB нижней границы  
        3. Отскок вверх от EMA50
        """
        if not self._can_trade():
            return False
        
        # Проверяем баланс
        if not self._should_prefer_direction("long"):
            return False
        
        # Мягкий RSI фильтр
        rsi_ok = self.rsi <= self.rsi_overbought
        if not rsi_ok:
            return False
        
        # Проверяем все типы сигналов
        signal_type = None
        signal_reason = None
        
        # 1. Ложный пробой BB
        bb_fakeout, fakeout_type = self._is_bb_lower_fakeout()
        if bb_fakeout:
            signal_type = "FAKEOUT"
            signal_reason = "BB_LOWER_FAKEOUT"
        
        # 2. Отскок от BB
        if not signal_type:
            bb_bounce, bounce_type = self._is_bb_lower_bounce()
            if bb_bounce:
                signal_type = "BOUNCE"
                signal_reason = "BB_LOWER_BOUNCE"
        
        # 3. Отскок от EMA
        if not signal_type:
            ema_bounce, ema_type = self._is_ema_bounce_up()
            if ema_bounce:
                signal_type = "BOUNCE"
                signal_reason = "EMA_BOUNCE_UP"
        
        if signal_type:
            self.log(f"🟢 LONG {signal_type}: {signal_reason}")
            self.log(f"   Price: ${self.close:.2f} | RSI: {self.rsi:.1f}")
            self.log(f"   BB: ${self.bb_lower:.2f} - ${self.bb_upper:.2f} | EMA: ${self.ema50:.2f}")
            self.entry_reason = signal_reason
            return True
        
        return False
    
    def should_short(self) -> bool:
        """
        Множественные условия для SHORT:
        1. Ложный пробой BB верхней границы
        2. Отскок от BB верхней границы
        3. Отскок вниз от EMA50
        """
        if not self._can_trade():
            return False
        
        # Проверяем баланс
        if not self._should_prefer_direction("short"):
            return False
        
        # Мягкий RSI фильтр
        rsi_ok = self.rsi >= self.rsi_oversold
        if not rsi_ok:
            return False
        
        # Проверяем все типы сигналов
        signal_type = None
        signal_reason = None
        
        # 1. Ложный пробой BB
        bb_fakeout, fakeout_type = self._is_bb_upper_fakeout()
        if bb_fakeout:
            signal_type = "FAKEOUT"
            signal_reason = "BB_UPPER_FAKEOUT"
        
        # 2. Отскок от BB
        if not signal_type:
            bb_bounce, bounce_type = self._is_bb_upper_bounce()
            if bb_bounce:
                signal_type = "BOUNCE"
                signal_reason = "BB_UPPER_BOUNCE"
        
        # 3. Отскок от EMA
        if not signal_type:
            ema_bounce, ema_type = self._is_ema_bounce_down()
            if ema_bounce:
                signal_type = "BOUNCE"
                signal_reason = "EMA_BOUNCE_DOWN"
        
        if signal_type:
            self.log(f"🔴 SHORT {signal_type}: {signal_reason}")
            self.log(f"   Price: ${self.close:.2f} | RSI: {self.rsi:.1f}")
            self.log(f"   BB: ${self.bb_lower:.2f} - ${self.bb_upper:.2f} | EMA: ${self.ema50:.2f}")
            self.entry_reason = signal_reason
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
            max_qty = (self.available_margin * 0.85) / entry_price
            return min(qty, max_qty, 0.4)
        else:
            return 0.001
    
    def go_long(self):
        """Открытие LONG позиции"""
        entry_price = self.close
        
        # Адаптивный стоп в зависимости от типа сигнала
        if hasattr(self, 'entry_reason') and 'BB' in self.entry_reason:
            # Для BB сигналов - стоп ниже BB
            if 'LOWER' in self.entry_reason:
                stop_loss_price = self.bb_lower - (self.atr * self.atr_stop_multiplier)
            else:
                stop_loss_price = entry_price - (self.atr * self.atr_stop_multiplier)
        else:
            # Для EMA сигналов - стоп ниже EMA
            stop_loss_price = self.ema50 - (self.atr * self.atr_stop_multiplier)
        
        # Адаптивная цель
        risk_distance = entry_price - stop_loss_price
        take_profit_price = entry_price + (risk_distance * 2.0)  # R:R = 1:2
        
        # Альтернативная цель: BB верхняя граница
        if 'BB_LOWER' in getattr(self, 'entry_reason', ''):
            bb_target = self.bb_middle  # До средней линии для начала
            if bb_target > entry_price:
                take_profit_price = max(take_profit_price, bb_target)
        
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
        self.total_longs += 1
        
        # Логирование
        risk_amount = qty * (entry_price - stop_loss_price)
        potential_profit = qty * (take_profit_price - entry_price)
        rr_ratio = potential_profit / risk_amount if risk_amount > 0 else 0
        
        self.log(f"=== ACTIVE LONG #{self.daily_trades_count} ===")
        self.log(f"Reason: {getattr(self, 'entry_reason', 'UNKNOWN')}")
        self.log(f"Size: {qty:.4f} @ ${entry_price:.2f}")
        self.log(f"Stop: ${stop_loss_price:.2f} | Target: ${take_profit_price:.2f}")
        self.log(f"Risk: ${risk_amount:.2f} | Potential: ${potential_profit:.2f} | R:R = 1:{rr_ratio:.1f}")
        
        total_trades = self.total_longs + self.total_shorts
        long_pct = (self.total_longs / total_trades * 100) if total_trades > 0 else 50
        self.log(f"Balance: {long_pct:.0f}% longs ({self.total_longs}L/{self.total_shorts}S)")
    
    def go_short(self):
        """Открытие SHORT позиции"""
        entry_price = self.close
        
        # Адаптивный стоп в зависимости от типа сигнала
        if hasattr(self, 'entry_reason') and 'BB' in self.entry_reason:
            # Для BB сигналов - стоп выше BB
            if 'UPPER' in self.entry_reason:
                stop_loss_price = self.bb_upper + (self.atr * self.atr_stop_multiplier)
            else:
                stop_loss_price = entry_price + (self.atr * self.atr_stop_multiplier)
        else:
            # Для EMA сигналов - стоп выше EMA
            stop_loss_price = self.ema50 + (self.atr * self.atr_stop_multiplier)
        
        # Адаптивная цель
        risk_distance = stop_loss_price - entry_price
        take_profit_price = entry_price - (risk_distance * 2.0)  # R:R = 1:2
        
        # Альтернативная цель: BB нижняя граница
        if 'BB_UPPER' in getattr(self, 'entry_reason', ''):
            bb_target = self.bb_middle  # До средней линии для начала
            if bb_target < entry_price:
                take_profit_price = min(take_profit_price, bb_target)
        
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
        self.total_shorts += 1
        
        # Логирование
        risk_amount = qty * (stop_loss_price - entry_price)
        potential_profit = qty * (entry_price - take_profit_price)
        rr_ratio = potential_profit / risk_amount if risk_amount > 0 else 0
        
        self.log(f"=== ACTIVE SHORT #{self.daily_trades_count} ===")
        self.log(f"Reason: {getattr(self, 'entry_reason', 'UNKNOWN')}")
        self.log(f"Size: {qty:.4f} @ ${entry_price:.2f}")
        self.log(f"Stop: ${stop_loss_price:.2f} | Target: ${take_profit_price:.2f}")
        self.log(f"Risk: ${risk_amount:.2f} | Potential: ${potential_profit:.2f} | R:R = 1:{rr_ratio:.1f}")
        
        total_trades = self.total_longs + self.total_shorts
        short_pct = (self.total_shorts / total_trades * 100) if total_trades > 0 else 50
        self.log(f"Balance: {short_pct:.0f}% shorts ({self.total_longs}L/{self.total_shorts}S)")
    
    def update_position(self):
        """Управление позицией"""
        if not self.position.is_open:
            return
        
        # Принудительное закрытие по времени
        if self.entry_bar and (self.index - self.entry_bar) >= self.max_holding_bars:
            self.liquidate()
            self.log(f"⏰ Time exit after {self.max_holding_bars*15} minutes")
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
            self.log(f"✅ Profit: ${pnl:.2f} | Great trade!")
        
        total_trades = self.total_longs + self.total_shorts
        long_pct = (self.total_longs / total_trades * 100) if total_trades > 0 else 50
        self.log(f"🎯 Closed @ ${order.price:.2f} | Daily: {self.daily_trades_count}/8 | Balance: {long_pct:.0f}%")
        self._reset_position()
    
    def before(self):
        """Мониторинг каждые 2 часа"""
        if self.index % 8 == 0 and self.index >= max(self.bb_period, self.ema_period) + 10:
            
            # Текущие позиции относительно уровней
            bb_pos = "ABOVE_BB" if self.close > self.bb_upper else "BELOW_BB" if self.close < self.bb_lower else "IN_BB"
            ema_pos = "↑" if self.close > self.ema50 else "↓"
            
            vol_ratio = self.current_volume / self.volume_ma if self.volume_ma > 0 else 1
            
            total_trades = self.total_longs + self.total_shorts
            long_pct = (self.total_longs / total_trades * 100) if total_trades > 0 else 50
            
            self.log(f"📊 Bar {self.index}: ${self.close:.2f} | {bb_pos} | EMA{ema_pos}")
            self.log(f"   BB: ${self.bb_lower:.2f}-${self.bb_upper:.2f} ({self.bb_width:.1f}%) | EMA: ${self.ema50:.2f}")
            self.log(f"   RSI: {self.rsi:.1f} | Vol: {vol_ratio:.1f}x")
            self.log(f"   Trades: {self.daily_trades_count}/8 | Balance: {long_pct:.0f}% ({self.total_longs}L/{self.total_shorts}S)")
            
            if self.position.is_open:
                bars_held = self.index - self.entry_bar if self.entry_bar else 0
                hours_held = bars_held * 15 / 60
                self.log(f"   Position: {self.position_type} {hours_held:.1f}h | P&L: ${self.position.pnl:.2f}")
