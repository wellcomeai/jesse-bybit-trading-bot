# strategies/AdaptiveMomentum/__init__.py
from jesse.strategies import Strategy
import jesse.indicators as ta
import numpy as np


class AdaptiveMomentum(Strategy):
    """
    Adaptive Momentum Strategy для крипторынка
    Торгует сильные импульсы на объёме, адаптируется к рыночным циклам
    """
    
    def __init__(self):
        super().__init__()
        
        # === ИНДИКАТОРЫ ===
        self.ema_fast = 21          # Быстрая EMA для тренда
        self.ema_slow = 50          # Медленная EMA для тренда
        self.rsi_period = 14        # RSI для фильтрации
        self.volume_ma_period = 20  # Средний объём
        self.atr_period = 14        # ATR для волатильности
        
        # === ПОРОГОВЫЕ ЗНАЧЕНИЯ ===
        self.min_candle_strength = 1.5    # Минимальная сила свечи в %
        self.volume_multiplier = 1.3      # Объём должен быть в 1.3x выше среднего
        self.rsi_overbought = 75          # RSI перекупленность
        self.rsi_oversold = 25            # RSI перепроданность
        
        # === УПРАВЛЕНИЕ РИСКАМИ ===
        self.risk_percent = 0.8           # Риск на сделку
        self.atr_stop_multiplier = 2.5    # Стоп-лосс = 2.5x ATR
        self.min_rr_ratio = 2.0           # Минимальное соотношение риск/прибыль
        self.max_holding_hours = 48       # Максимум часов в позиции
        
        # === АДАПТИВНОСТЬ ===
        self.market_regime_period = 100   # Период для определения режима рынка
        self.bull_threshold = 0.02        # Порог бычьего рынка (+2% за период)
        self.bear_threshold = -0.02       # Порог медвежьего рынка (-2% за период)
        
        # === СОСТОЯНИЕ ===
        self.entry_bar = None
        self.position_type = None
        self.market_regime = "NEUTRAL"    # BULL, BEAR, NEUTRAL
        self.consecutive_losses = 0
        self.last_regime_update = 0
        
        self.log(f"=== ADAPTIVE MOMENTUM INITIALIZED ===")
        self.log(f"EMA: {self.ema_fast}/{self.ema_slow}")
        self.log(f"Risk: {self.risk_percent}% per trade")
        self.log(f"ATR Stop: {self.atr_stop_multiplier}x ATR")

    # === СВОЙСТВА ИНДИКАТОРОВ ===
    @property
    def ema21(self):
        return ta.ema(self.candles, period=self.ema_fast)
    
    @property
    def ema50(self):
        return ta.ema(self.candles, period=self.ema_slow)
    
    @property
    def rsi(self):
        return ta.rsi(self.candles, period=self.rsi_period)
    
    @property
    def volume_ma(self):
        return ta.sma(self.candles[:, 5], period=self.volume_ma_period)  # Volume
    
    @property
    def atr(self):
        return ta.atr(self.candles, period=self.atr_period)
    
    @property
    def current_volume(self):
        return self.candles[-1, 5]  # Текущий объём
    
    # === АНАЛИЗ РЫНКА ===
    def _update_market_regime(self):
        """Определяем текущий режим рынка: BULL/BEAR/NEUTRAL"""
        if self.index - self.last_regime_update < 24:  # Обновляем раз в сутки
            return
            
        if self.index < self.market_regime_period:
            return
            
        # Изменение цены за период
        price_change = (self.close - self.candles[-self.market_regime_period, 4]) / self.candles[-self.market_regime_period, 4]
        
        # Определяем режим
        if price_change > self.bull_threshold:
            self.market_regime = "BULL"
        elif price_change < self.bear_threshold:
            self.market_regime = "BEAR"
        else:
            self.market_regime = "NEUTRAL"
            
        self.last_regime_update = self.index
        self.log(f"🔄 Market regime: {self.market_regime} (change: {price_change*100:.1f}%)")
    
    def _is_strong_bullish_candle(self):
        """Проверяем силу бычьей свечи"""
        # Размер тела свечи
        body_size = (self.close - self.open) / self.open * 100
        
        # Свеча должна быть зелёной и достаточно сильной
        is_green = self.close > self.open
        is_strong = body_size >= self.min_candle_strength
        
        return is_green and is_strong
    
    def _is_strong_bearish_candle(self):
        """Проверяем силу медвежьей свечи"""
        # Размер тела свечи
        body_size = abs(self.close - self.open) / self.open * 100
        
        # Свеча должна быть красной и достаточно сильной
        is_red = self.close < self.open
        is_strong = body_size >= self.min_candle_strength
        
        return is_red and is_strong
    
    def _has_volume_spike(self):
        """Проверяем всплеск объёма"""
        return self.current_volume > (self.volume_ma * self.volume_multiplier)
    
    def _get_trend_direction(self):
        """Определяем направление тренда"""
        if self.close > self.ema21 > self.ema50:
            return "UP"
        elif self.close < self.ema21 < self.ema50:
            return "DOWN"
        else:
            return "SIDEWAYS"
    
    def _can_trade(self):
        """Базовые условия для торговли"""
        # Достаточно данных
        if self.index < max(self.ema_slow, self.market_regime_period):
            return False
            
        # Нет открытой позиции
        if self.position.is_open:
            return False
            
        # Не слишком много убытков подряд
        if self.consecutive_losses >= 4:
            return False
            
        return True
    
    def _should_long_by_regime(self):
        """Проверяем возможность лонга в зависимости от режима рынка"""
        if self.market_regime == "BULL":
            return True  # В бычьем рынке лонги приоритет
        elif self.market_regime == "BEAR":
            return self.rsi < 30  # В медвежьем рынке лонги только при сильной перепроданности
        else:
            return True  # В нейтральном рынке разрешены
    
    def _should_short_by_regime(self):
        """Проверяем возможность шорта в зависимости от режима рынка"""
        if self.market_regime == "BEAR":
            return True  # В медвежьем рынке шорты приоритет
        elif self.market_regime == "BULL":
            return self.rsi > 70  # В бычьем рынке шорты только при сильной перекупленности
        else:
            return True  # В нейтральном рынке разрешены

    # === УСЛОВИЯ ВХОДА ===
    def should_long(self) -> bool:
        """
        Условия для LONG:
        1. Сильная зелёная свеча (>1.5%)
        2. Всплеск объёма (>1.3x среднего)
        3. Восходящий тренд (цена > EMA21 > EMA50)
        4. RSI не перекуплен (<75)
        5. Режим рынка позволяет лонги
        """
        if not self._can_trade():
            return False
            
        # Обновляем режим рынка
        self._update_market_regime()
        
        # Проверяем условия
        strong_candle = self._is_strong_bullish_candle()
        volume_spike = self._has_volume_spike()
        trend_up = self._get_trend_direction() == "UP"
        rsi_ok = self.rsi < self.rsi_overbought
        regime_allows = self._should_long_by_regime()
        
        if strong_candle and volume_spike and trend_up and rsi_ok and regime_allows:
            candle_strength = (self.close - self.open) / self.open * 100
            self.log(f"🟢 LONG SIGNAL:")
            self.log(f"   Candle: +{candle_strength:.2f}%")
            self.log(f"   Volume: {self.current_volume/self.volume_ma:.1f}x avg")
            self.log(f"   RSI: {self.rsi:.1f}")
            self.log(f"   Market: {self.market_regime}")
            return True
            
        return False
    
    def should_short(self) -> bool:
        """
        Условия для SHORT:
        1. Сильная красная свеча (>1.5%)
        2. Всплеск объёма (>1.3x среднего)
        3. Нисходящий тренд (цена < EMA21 < EMA50)
        4. RSI не перепродан (>25)
        5. Режим рынка позволяет шорты
        """
        if not self._can_trade():
            return False
            
        # Обновляем режим рынка
        self._update_market_regime()
        
        # Проверяем условия
        strong_candle = self._is_strong_bearish_candle()
        volume_spike = self._has_volume_spike()
        trend_down = self._get_trend_direction() == "DOWN"
        rsi_ok = self.rsi > self.rsi_oversold
        regime_allows = self._should_short_by_regime()
        
        if strong_candle and volume_spike and trend_down and rsi_ok and regime_allows:
            candle_strength = abs(self.close - self.open) / self.open * 100
            self.log(f"🔴 SHORT SIGNAL:")
            self.log(f"   Candle: -{candle_strength:.2f}%")
            self.log(f"   Volume: {self.current_volume/self.volume_ma:.1f}x avg")
            self.log(f"   RSI: {self.rsi:.1f}")
            self.log(f"   Market: {self.market_regime}")
            return True
            
        return False
    
    def should_cancel_entry(self) -> bool:
        return False
    
    # === УПРАВЛЕНИЕ ПОЗИЦИЯМИ ===
    def _calculate_position_size(self, entry_price, stop_loss_price):
        """Расчёт размера позиции на основе риска"""
        risk_amount = self.available_margin * (self.risk_percent / 100)
        price_diff = abs(entry_price - stop_loss_price)
        
        if price_diff > 0:
            qty = risk_amount / price_diff
            # Ограничиваем максимальным размером
            max_qty = (self.available_margin * 0.8) / entry_price
            return min(qty, max_qty, 0.1)  # Максимум 0.1 BTC за сделку
        else:
            return 0.001
    
    def go_long(self):
        """Открытие длинной позиции"""
        entry_price = self.close
        
        # Динамический стоп-лосс на основе ATR
        atr_stop = self.atr * self.atr_stop_multiplier
        stop_loss_price = entry_price - atr_stop
        
        # Тейк-профит на основе соотношения риск/прибыль
        risk_amount = entry_price - stop_loss_price
        take_profit_price = entry_price + (risk_amount * self.min_rr_ratio)
        
        qty = self._calculate_position_size(entry_price, stop_loss_price)
        
        # Размещаем ордера
        self.buy = qty, entry_price
        self.stop_loss = qty, stop_loss_price
        self.take_profit = qty, take_profit_price
        
        # Сохраняем состояние
        self.entry_bar = self.index
        self.position_type = 'LONG'
        
        # Логирование
        self.log(f"=== LONG POSITION OPENED ===")
        self.log(f"Size: {qty:.4f} BTC @ ${entry_price:.2f}")
        self.log(f"Stop Loss: ${stop_loss_price:.2f} (ATR: {atr_stop:.2f})")
        self.log(f"Take Profit: ${take_profit_price:.2f} (R:R = 1:{self.min_rr_ratio})")
        self.log(f"Risk: ${qty * risk_amount:.2f}")
    
    def go_short(self):
        """Открытие короткой позиции"""
        entry_price = self.close
        
        # Динамический стоп-лосс на основе ATR
        atr_stop = self.atr * self.atr_stop_multiplier
        stop_loss_price = entry_price + atr_stop
        
        # Тейк-профит на основе соотношения риск/прибыль
        risk_amount = stop_loss_price - entry_price
        take_profit_price = entry_price - (risk_amount * self.min_rr_ratio)
        
        qty = self._calculate_position_size(entry_price, stop_loss_price)
        
        # Размещаем ордера
        self.sell = qty, entry_price
        self.stop_loss = qty, stop_loss_price
        self.take_profit = qty, take_profit_price
        
        # Сохраняем состояние
        self.entry_bar = self.index
        self.position_type = 'SHORT'
        
        # Логирование
        self.log(f"=== SHORT POSITION OPENED ===")
        self.log(f"Size: {qty:.4f} BTC @ ${entry_price:.2f}")
        self.log(f"Stop Loss: ${stop_loss_price:.2f} (ATR: {atr_stop:.2f})")
        self.log(f"Take Profit: ${take_profit_price:.2f} (R:R = 1:{self.min_rr_ratio})")
        self.log(f"Risk: ${qty * risk_amount:.2f}")
    
    def update_position(self):
        """Управление открытой позицией"""
        if not self.position.is_open:
            return
            
        # Принудительное закрытие по времени
        if self.entry_bar and (self.index - self.entry_bar) >= self.max_holding_hours:
            self.liquidate()
            self.log(f"🕐 Position closed by time limit ({self.max_holding_hours}h)")
            self.log(f"Final P&L: ${self.position.pnl:.2f}")
            self._reset_position()
    
    def _reset_position(self):
        """Сброс переменных позиции"""
        self.entry_bar = None
        self.position_type = None
    
    def on_close_position(self, order):
        """Обработка закрытия позиции"""
        pnl = self.position.pnl
        
        # Обновляем статистику
        if pnl < 0:
            self.consecutive_losses += 1
            self.log(f"❌ Loss: ${pnl:.2f} | Consecutive losses: {self.consecutive_losses}")
        else:
            self.consecutive_losses = 0
            self.log(f"✅ Profit: ${pnl:.2f} | Reset loss counter")
        
        self.log(f"🔚 Position closed @ ${order.price:.2f}")
        self.log(f"Market regime was: {self.market_regime}")
        
        self._reset_position()
    
    def before(self):
        """Отладочная информация"""
        # Каждые 24 часа показываем состояние
        if self.index % 24 == 0 and self.index >= self.ema_slow:
            trend = self._get_trend_direction()
            vol_ratio = self.current_volume / self.volume_ma if self.volume_ma > 0 else 1
            
            self.log(f"📊 Hour {self.index}: ${self.close:.2f}")
            self.log(f"   Trend: {trend} | RSI: {self.rsi:.1f} | Vol: {vol_ratio:.1f}x")
            self.log(f"   Market: {self.market_regime} | Losses: {self.consecutive_losses}")
            
            if self.position.is_open:
                hours_held = self.index - self.entry_bar if self.entry_bar else 0
                self.log(f"   Position: {self.position_type} {hours_held}h | P&L: ${self.position.pnl:.2f}")
