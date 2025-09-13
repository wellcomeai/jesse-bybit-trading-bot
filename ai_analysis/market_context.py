# ai_analysis/market_context.py
import aiohttp
import asyncio
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import json


class MarketContextCollector:
    """
    Собирает дополнительный рыночный контекст для ИИ анализа
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache = {}  # Простой кэш для избежания лишних запросов
        self.cache_ttl = 300  # 5 минут
        
        logging.info("📊 Сборщик рыночного контекста инициализирован")
    
    async def collect_context(self, symbol: str, timeframe: str, candles_data: np.ndarray) -> Dict[str, Any]:
        """
        Собирает полный рыночный контекст
        
        Args:
            symbol: Торговая пара (например, BTCUSDT)
            timeframe: Таймфрейм (например, 15m)  
            candles_data: Данные свечей из Jesse
            
        Returns:
            Словарь с рыночным контекстом
        """
        try:
            context = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'timeframe': timeframe
            }
            
            # Анализируем свечи из Jesse
            if len(candles_data) > 0:
                context.update(await self._analyze_candles(candles_data))
            
            # Получаем дополнительные рыночные данные
            context.update(await self._get_market_sentiment(symbol))
            context.update(await self._calculate_volatility_metrics(candles_data))
            context.update(await self._analyze_volume_profile(candles_data))
            
            return context
            
        except Exception as e:
            logging.error(f"❌ Ошибка сбора рыночного контекста: {e}")
            return self._get_default_context(symbol, timeframe)
    
    async def _analyze_candles(self, candles: np.ndarray) -> Dict[str, Any]:
        """
        Анализирует свечи для определения паттернов и трендов
        """
        try:
            if len(candles) < 20:
                return {'candle_analysis': 'insufficient_data'}
            
            # Берем последние 20 свечей для анализа
            recent_candles = candles[-20:]
            closes = recent_candles[:, 4].astype(float)  # Цены закрытия
            highs = recent_candles[:, 2].astype(float)   # Максимумы
            lows = recent_candles[:, 3].astype(float)    # Минимумы
            volumes = recent_candles[:, 5].astype(float) # Объемы
            
            return {
                'price_trend': self._determine_price_trend(closes),
                'support_resistance': self._find_support_resistance(highs, lows),
                'candle_patterns': self._identify_candle_patterns(recent_candles),
                'momentum': self._calculate_momentum(closes),
                'volume_trend': self._analyze_volume_trend(volumes)
            }
            
        except Exception as e:
            logging.warning(f"⚠️ Ошибка анализа свечей: {e}")
            return {'candle_analysis': 'error'}
    
    def _determine_price_trend(self, closes: np.ndarray) -> str:
        """
        Определяет ценовой тренд
        """
        if len(closes) < 5:
            return 'UNKNOWN'
        
        # Сравниваем последние 5 свечей с предыдущими 5
        recent_avg = np.mean(closes[-5:])
        previous_avg = np.mean(closes[-10:-5])
        
        change_percent = (recent_avg - previous_avg) / previous_avg * 100
        
        if change_percent > 2:
            return 'STRONG_UPTREND'
        elif change_percent > 0.5:
            return 'UPTREND'
        elif change_percent < -2:
            return 'STRONG_DOWNTREND'
        elif change_percent < -0.5:
            return 'DOWNTREND'
        else:
            return 'SIDEWAYS'
    
    def _find_support_resistance(self, highs: np.ndarray, lows: np.ndarray) -> Dict[str, float]:
        """
        Находит уровни поддержки и сопротивления
        """
        try:
            current_price = highs[-1]  # Используем последний максимум как текущую цену
            
            # Находим локальные максимумы и минимумы
            resistance_levels = []
            support_levels = []
            
            for i in range(2, len(highs) - 2):
                # Локальный максимум
                if highs[i] > highs[i-1] and highs[i] > highs[i+1] and highs[i] > highs[i-2] and highs[i] > highs[i+2]:
                    resistance_levels.append(highs[i])
                
                # Локальный минимум
                if lows[i] < lows[i-1] and lows[i] < lows[i+1] and lows[i] < lows[i-2] and lows[i] < lows[i+2]:
                    support_levels.append(lows[i])
            
            # Берем ближайшие уровни
            resistance_levels = sorted(resistance_levels, key=lambda x: abs(x - current_price))
            support_levels = sorted(support_levels, key=lambda x: abs(x - current_price))
            
            return {
                'nearest_resistance': resistance_levels[0] if resistance_levels else current_price * 1.02,
                'nearest_support': support_levels[0] if support_levels else current_price * 0.98,
                'resistance_strength': len([r for r in resistance_levels if abs(r - current_price) / current_price < 0.05]),
                'support_strength': len([s for s in support_levels if abs(s - current_price) / current_price < 0.05])
            }
            
        except Exception as e:
            logging.warning(f"⚠️ Ошибка поиска уровней: {e}")
            return {}
    
    def _identify_candle_patterns(self, candles: np.ndarray) -> List[str]:
        """
        Идентифицирует свечные паттерны
        """
        patterns = []
        
        if len(candles) < 3:
            return patterns
        
        try:
            # Берем последние 3 свечи
            last_3 = candles[-3:]
            
            for i, candle in enumerate(last_3):
                open_price = float(candle[1])
                high_price = float(candle[2])
                low_price = float(candle[3])
                close_price = float(candle[4])
                
                body = abs(close_price - open_price)
                total_range = high_price - low_price
                
                if total_range == 0:
                    continue
                
                body_ratio = body / total_range
                
                # Доджи
                if body_ratio < 0.1:
                    patterns.append(f'DOJI_{i}')
                
                # Молот/повешенный
                upper_shadow = high_price - max(open_price, close_price)
                lower_shadow = min(open_price, close_price) - low_price
                
                if lower_shadow > body * 2 and upper_shadow < body * 0.5:
                    patterns.append(f'HAMMER_{i}')
                
                if upper_shadow > body * 2 and lower_shadow < body * 0.5:
                    patterns.append(f'SHOOTING_STAR_{i}')
                
                # Большие тела
                if body_ratio > 0.7:
                    if close_price > open_price:
                        patterns.append(f'BIG_GREEN_{i}')
                    else:
                        patterns.append(f'BIG_RED_{i}')
            
            return patterns
            
        except Exception as e:
            logging.warning(f"⚠️ Ошибка анализа паттернов: {e}")
            return []
    
    def _calculate_momentum(self, closes: np.ndarray) -> Dict[str, float]:
        """
        Рассчитывает моментум
        """
        try:
            if len(closes) < 10:
                return {}
            
            # Моментум за разные периоды
            momentum_5 = (closes[-1] - closes[-6]) / closes[-6] * 100
            momentum_10 = (closes[-1] - closes[-11]) / closes[-11] * 100
            
            # Скорость изменения
            roc = (closes[-1] - closes[-5]) / closes[-5] * 100
            
            return {
                'momentum_5': momentum_5,
                'momentum_10': momentum_10,
                'rate_of_change': roc,
                'momentum_direction': 'BULLISH' if momentum_5 > 0 and momentum_10 > 0 else 'BEARISH' if momentum_5 < 0 and momentum_10 < 0 else 'MIXED'
            }
            
        except Exception as e:
            logging.warning(f"⚠️ Ошибка расчета моментума: {e}")
            return {}
    
    def _analyze_volume_trend(self, volumes: np.ndarray) -> Dict[str, Any]:
        """
        Анализирует тренд объемов
        """
        try:
            if len(volumes) < 10:
                return {}
            
            # Сравниваем последние объемы со средними
            recent_volume_avg = np.mean(volumes[-5:])
            previous_volume_avg = np.mean(volumes[-10:-5])
            
            volume_change = (recent_volume_avg - previous_volume_avg) / previous_volume_avg * 100
            
            # Максимальный объем в выборке
            max_volume = np.max(volumes)
            current_volume = volumes[-1]
            
            return {
                'volume_trend': 'INCREASING' if volume_change > 20 else 'DECREASING' if volume_change < -20 else 'STABLE',
                'volume_change_percent': volume_change,
                'volume_vs_max': (current_volume / max_volume * 100) if max_volume > 0 else 0,
                'volume_spike': current_volume > recent_volume_avg * 1.5
            }
            
        except Exception as e:
            logging.warning(f"⚠️ Ошибка анализа объемов: {e}")
            return {}
    
    async def _get_market_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Получает рыночное настроение (упрощенная версия)
        """
        # В реальной версии здесь можно подключить Fear & Greed Index,
        # новостные сентименты, social sentiment и т.д.
        
        # Пока возвращаем базовую информацию
        return {
            'sentiment': 'NEUTRAL',  # BULLISH, BEARISH, NEUTRAL
            'sentiment_score': 50,   # 0-100
            'sentiment_source': 'default'
        }
    
    async def _calculate_volatility_metrics(self, candles: np.ndarray) -> Dict[str, Any]:
        """
        Рассчитывает метрики волатильности
        """
        try:
            if len(candles) < 20:
                return {'volatility': 'UNKNOWN'}
            
            # Берем последние 20 свечей
            recent_candles = candles[-20:]
            closes = recent_candles[:, 4].astype(float)
            
            # Стандартное отклонение доходностей
            returns = np.diff(closes) / closes[:-1] * 100
            volatility = np.std(returns)
            
            # Средний истинный диапазон (упрощенная версия)
            highs = recent_candles[:, 2].astype(float)
            lows = recent_candles[:, 3].astype(float)
            
            true_ranges = []
            for i in range(1, len(recent_candles)):
                tr1 = highs[i] - lows[i]
                tr2 = abs(highs[i] - closes[i-1])
                tr3 = abs(lows[i] - closes[i-1])
                true_ranges.append(max(tr1, tr2, tr3))
            
            atr = np.mean(true_ranges)
            atr_percent = (atr / closes[-1]) * 100
            
            # Классификация волатильности
            if volatility > 3:
                vol_level = 'HIGH'
            elif volatility > 1:
                vol_level = 'MEDIUM'
            else:
                vol_level = 'LOW'
            
            return {
                'volatility': vol_level,
                'volatility_percent': volatility,
                'atr': atr,
                'atr_percent': atr_percent
            }
            
        except Exception as e:
            logging.warning(f"⚠️ Ошибка расчета волатильности: {e}")
            return {'volatility': 'UNKNOWN'}
    
    async def _analyze_volume_profile(self, candles: np.ndarray) -> Dict[str, Any]:
        """
        Анализирует профиль объема
        """
        try:
            if len(candles) < 10:
                return {}
            
            recent_candles = candles[-10:]
            volumes = recent_candles[:, 5].astype(float)
            
            # Средний объем
            avg_volume = np.mean(volumes)
            current_volume = volumes[-1]
            
            # Объем выше/ниже среднего
            above_avg_count = len([v for v in volumes if v > avg_volume])
            
            return {
                'avg_volume': avg_volume,
                'current_volume': current_volume,
                'volume_ratio': (current_volume / avg_volume) if avg_volume > 0 else 1,
                'above_average_frequency': (above_avg_count / len(volumes)) * 100
            }
            
        except Exception as e:
            logging.warning(f"⚠️ Ошибка анализа профиля объема: {e}")
            return {}
    
    def _get_default_context(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Возвращает контекст по умолчанию при ошибках
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'timeframe': timeframe,
            'sentiment': 'NEUTRAL',
            'volatility': 'MEDIUM',
            'data_quality': 'LIMITED',
            'error': 'Failed to collect full context'
        }
    
    async def __aenter__(self):
        """Асинхронный контекстный менеджер"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()
