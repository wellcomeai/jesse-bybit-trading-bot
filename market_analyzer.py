# market_analyzer.py - ИСПРАВЛЕНО для работы в event loop
import asyncio
from typing import Dict, Any, List
import requests
import numpy as np
from datetime import datetime
import logging

class MarketAnalyzer:
    """
    ИСПРАВЛЕННЫЙ анализатор рынка БЕЗ конфликта event loop
    """
    
    def __init__(self):
        # Убираем создание AI analyzer и context collector здесь
        # чтобы избежать конфликтов event loop
        self.logger = logging.getLogger(__name__)
        
        # Список активных стратегий
        self.strategies = [
            {'name': 'ActiveScalper', 'timeframe': '5m'},
            {'name': 'BalancedTrader', 'timeframe': '15m'}, 
            {'name': 'QualityTrader', 'timeframe': '1h'}
        ]

    async def analyze_all_strategies(self) -> Dict[str, Any]:
        """ИСПРАВЛЕНО: Анализирует рынок по всем стратегиям без конфликта event loop"""
        try:
            # 1. Получаем текущие данные с биржи (СИНХРОННО)
            current_data = self._get_current_market_data_sync()
            
            # 2. Анализируем каждую стратегию (СИНХРОННО)
            strategy_analyses = []
            for strategy in self.strategies:
                analysis = self._analyze_strategy_sync(strategy, current_data)
                strategy_analyses.append(analysis)
            
            # 3. Делаем ИИ анализ (АСИНХРОННО, но безопасно)
            overall_analysis = await self._get_ai_market_overview_safe(strategy_analyses, current_data)
            
            return {
                'timestamp': current_data['timestamp'],
                'price': current_data['price'],
                'strategy_analyses': strategy_analyses,
                'overall_analysis': overall_analysis,
                'market_phase': self._determine_market_phase(strategy_analyses),
                'recommendations': overall_analysis.get('recommendations', [])
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа стратегий: {e}")
            return self._get_fallback_analysis_data()

    def _get_current_market_data_sync(self) -> Dict[str, Any]:
        """ИСПРАВЛЕНО: Получает актуальные данные с Bybit СИНХРОННО"""
        try:
            # Получаем последние свечи СИНХРОННО
            response = requests.get(
                'https://api-testnet.bybit.com/v5/market/kline',
                params={
                    'category': 'linear',
                    'symbol': 'BTCUSDT',
                    'interval': '5',  # 5 минут
                    'limit': 50  # Уменьшаем количество для скорости
                },
                timeout=10
            )
            
            data = response.json()
            if data['retCode'] == 0:
                candles = data['result']['list']
                
                # Преобразуем в numpy array
                candle_data = []
                for candle in candles[:20]:  # Берем только 20 последних
                    candle_data.append([
                        int(candle[0]),      # timestamp
                        float(candle[1]),    # open
                        float(candle[2]),    # high
                        float(candle[3]),    # low
                        float(candle[4]),    # close
                        float(candle[5])     # volume
                    ])
                
                candles_array = np.array(candle_data)
                current_price = float(candles[0][4])
                
                # Рассчитываем изменение за 24ч (упрощенно)
                if len(candles) > 10:
                    old_price = float(candles[10][4])
                    change_24h = ((current_price - old_price) / old_price) * 100
                else:
                    change_24h = 0
                
                return {
                    'timestamp': candles[0][0],
                    'price': current_price,
                    'candles': candles_array,
                    'volume_24h': sum([float(c[5]) for c in candles[:20]]),
                    'change_24h': change_24h
                }
            else:
                raise Exception(f"Bybit API error: {data['retMsg']}")
                
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка получения данных с Bybit: {e}")
            return self._get_mock_data()

    def _get_mock_data(self) -> Dict[str, Any]:
        """Заглушка на случай ошибки API"""
        import random
        base_price = 43000
        mock_price = base_price + random.randint(-2000, 2000)
        
        return {
            'timestamp': str(int(datetime.now().timestamp() * 1000)),
            'price': mock_price,
            'candles': np.zeros((20, 6)),
            'volume_24h': 1000000,
            'change_24h': random.uniform(-5, 5)
        }

    def _analyze_strategy_sync(self, strategy: Dict, market_data: Dict) -> Dict[str, Any]:
        """ИСПРАВЛЕНО: Анализирует рынок с точки зрения конкретной стратегии СИНХРОННО"""
        
        candles = market_data['candles']
        current_price = market_data['price']
        
        # Упрощенные индикаторы без использования jesse.indicators
        if strategy['name'] == 'ActiveScalper':
            signal = self._get_scalper_signal(current_price, candles)
            confidence = 75 if 'BUY' in signal else 60
        elif strategy['name'] == 'BalancedTrader':
            signal = self._get_balanced_signal(current_price, market_data['change_24h'])
            confidence = 70 if abs(market_data['change_24h']) < 3 else 50
        elif strategy['name'] == 'QualityTrader':
            signal = self._get_quality_signal(current_price, market_data['volume_24h'])
            confidence = 80 if market_data['volume_24h'] > 500000 else 40
        else:
            signal = 'NEUTRAL'
            confidence = 50
        
        return {
            'strategy': strategy['name'],
            'timeframe': strategy['timeframe'],
            'signal': signal,
            'confidence': confidence,
            'current_price': current_price
        }

    def _get_scalper_signal(self, price: float, candles: np.ndarray) -> str:
        """Упрощенный сигнал для скальпера"""
        if len(candles) < 5:
            return 'NEUTRAL'
        
        # Простая логика на основе последних 5 свечей
        recent_closes = candles[-5:, 4]  # Последние 5 цен закрытия
        avg_price = np.mean(recent_closes)
        
        if price > avg_price * 1.002:  # На 0.2% выше средней
            return 'BUY'
        elif price < avg_price * 0.998:  # На 0.2% ниже средней
            return 'SELL'
        else:
            return 'NEUTRAL'

    def _get_balanced_signal(self, price: float, change_24h: float) -> str:
        """Упрощенный сигнал для сбалансированной стратегии"""
        if change_24h > 2:
            return 'BUY'
        elif change_24h < -2:
            return 'SELL'
        else:
            return 'HOLD'

    def _get_quality_signal(self, price: float, volume_24h: float) -> str:
        """Упрощенный сигнал для качественной стратегии"""
        if volume_24h > 800000:  # Высокий объем
            if price > 43000:
                return 'STRONG_BUY'
            else:
                return 'BUY'
        elif volume_24h < 300000:  # Низкий объем
            return 'NEUTRAL'
        else:
            return 'HOLD'

    async def _get_ai_market_overview_safe(self, strategy_analyses: List, market_data: Dict) -> Dict[str, Any]:
        """ИСПРАВЛЕНО: Безопасный ИИ анализ без конфликта event loop"""
        try:
            # Проверяем доступность OpenAI
            import os
            openai_key = os.getenv('OPENAI_API_KEY')
            if not openai_key:
                return self._get_mock_ai_analysis(strategy_analyses, market_data)
            
            # Пытаемся сделать ИИ анализ
            try:
                # ИСПРАВЛЕНИЕ: Используем aiohttp вместо создания нового event loop
                import aiohttp
                
                prompt = self._build_market_analysis_prompt(strategy_analyses, market_data)
                
                headers = {
                    'Authorization': f'Bearer {openai_key}',
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'model': os.getenv('OPENAI_MODEL', 'gpt-4'),
                    'messages': [
                        {
                            "role": "system", 
                            "content": self._get_market_analysis_system_prompt()
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    'temperature': 0.3,
                    'max_tokens': 1000
                }
                
                # Используем текущий event loop
                timeout = aiohttp.ClientTimeout(total=15)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post('https://api.openai.com/v1/chat/completions', 
                                          headers=headers, json=payload) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            ai_text = data['choices'][0]['message']['content']
                            return self._parse_ai_response_safe(ai_text)
                        else:
                            self.logger.warning(f"⚠️ OpenAI API вернул {response.status}")
                            return self._get_mock_ai_analysis(strategy_analyses, market_data)
                            
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка OpenAI API: {e}")
                return self._get_mock_ai_analysis(strategy_analyses, market_data)
                
        except Exception as e:
            self.logger.error(f"❌ Общая ошибка ИИ анализа: {e}")
            return self._get_mock_ai_analysis(strategy_analyses, market_data)

    def _get_mock_ai_analysis(self, strategy_analyses: List, market_data: Dict) -> Dict[str, Any]:
        """Мок ИИ анализа на случай ошибок"""
        price = market_data.get('price', 43000)
        change_24h = market_data.get('change_24h', 0)
        
        # Определяем фазу рынка на основе данных
        if change_24h > 3:
            market_phase = "BULLISH"
            confidence = 75
            insights = [
                "Рынок показывает сильный восходящий тренд",
                "Рекомендуется осторожная покупка"
            ]
        elif change_24h < -3:
            market_phase = "BEARISH"  
            confidence = 70
            insights = [
                "Рынок в коррекции",
                "Возможны дальнейшие снижения"
            ]
        else:
            market_phase = "NEUTRAL"
            confidence = 60
            insights = [
                "Рынок в боковом движении",
                "Ожидание четкого направления"
            ]
        
        return {
            "market_phase": market_phase,
            "confidence": confidence,
            "key_insights": insights,
            "recommendations": [
                "Следить за уровнем $43,000",
                "Использовать стоп-лоссы"
            ],
            "risk_level": "MEDIUM",
            "summary": f"Рынок находится в {market_phase.lower()} фазе с уверенностью {confidence}%"
        }

    def _build_market_analysis_prompt(self, strategy_analyses: List, market_data: Dict) -> str:
        """Строит промпт для ИИ анализа"""
        price = market_data.get('price', 0)
        change_24h = market_data.get('change_24h', 0)
        volume_24h = market_data.get('volume_24h', 0)
        
        prompt = f"""АНАЛИЗ РЫНКА BTC:

=== ТЕКУЩИЕ ДАННЫЕ ===
Цена: ${price:,.2f}
Изменение 24ч: {change_24h:+.2f}%
Объем 24ч: {volume_24h:,.0f}

=== АНАЛИЗ ПО СТРАТЕГИЯМ ==="""

        for analysis in strategy_analyses:
            prompt += f"""

{analysis['strategy']} ({analysis['timeframe']}):
- Сигнал: {analysis['signal']}
- Уверенность: {analysis['confidence']}%"""

        prompt += f"""

ПРОАНАЛИЗИРУЙ общее состояние рынка и дай рекомендации в JSON формате."""
        
        return prompt

    def _get_market_analysis_system_prompt(self) -> str:
        """Системный промпт для анализа рынка"""
        return """Ты - эксперт по анализу криптовалютных рынков.

ЗАДАЧА: Проанализировать общее состояние рынка BTC на основе данных от торговых стратегий.

ФОРМАТ ОТВЕТА (строго JSON):
{
    "market_phase": "BULLISH|BEARISH|NEUTRAL|VOLATILE",
    "confidence": 0-100,
    "key_insights": ["инсайт1", "инсайт2"],
    "recommendations": ["рекомендация1", "рекомендация2"],
    "risk_level": "LOW|MEDIUM|HIGH",
    "summary": "краткая сводка в 2-3 предложения"
}

Анализируй объективно, учитывая все данные."""

    def _parse_ai_response_safe(self, response_text: str) -> Dict[str, Any]:
        """Безопасный парсинг ответа ИИ"""
        try:
            import json
            
            # Ищем JSON в тексте
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_text = response_text[start_idx:end_idx + 1]
                parsed = json.loads(json_text)
                
                # Валидация обязательных полей
                required_fields = ['market_phase', 'confidence', 'summary']
                for field in required_fields:
                    if field not in parsed:
                        parsed[field] = self._get_default_ai_value(field)
                
                return parsed
            else:
                raise ValueError("JSON не найден в ответе")
                
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка парсинга ИИ ответа: {e}")
            return {
                "market_phase": "NEUTRAL",
                "confidence": 50,
                "key_insights": ["Ошибка парсинга ИИ анализа"],
                "recommendations": ["Используйте базовый анализ"],
                "risk_level": "MEDIUM",
                "summary": "ИИ анализ недоступен, используется базовый анализ"
            }

    def _get_default_ai_value(self, field: str) -> Any:
        """Значения по умолчанию для полей ИИ анализа"""
        defaults = {
            "market_phase": "NEUTRAL",
            "confidence": 50,
            "summary": "Анализ требует уточнения",
            "key_insights": [],
            "recommendations": [],
            "risk_level": "MEDIUM"
        }
        return defaults.get(field, "Unknown")

    def _determine_market_phase(self, strategy_analyses: List) -> str:
        """Определяет общую фазу рынка на основе сигналов стратегий"""
        buy_signals = sum(1 for analysis in strategy_analyses if 'BUY' in analysis['signal'])
        sell_signals = sum(1 for analysis in strategy_analyses if 'SELL' in analysis['signal'])
        
        if buy_signals > sell_signals + 1:
            return "BULLISH"
        elif sell_signals > buy_signals + 1:
            return "BEARISH"
        else:
            return "NEUTRAL"

    def _get_fallback_analysis_data(self) -> Dict[str, Any]:
        """Данные анализа по умолчанию при ошибках"""
        current_time = int(datetime.now().timestamp() * 1000)
        
        return {
            'timestamp': str(current_time),
            'price': 43000,
            'strategy_analyses': [
                {'strategy': 'ActiveScalper', 'timeframe': '5m', 'signal': 'NEUTRAL', 'confidence': 50},
                {'strategy': 'BalancedTrader', 'timeframe': '15m', 'signal': 'HOLD', 'confidence': 50},
                {'strategy': 'QualityTrader', 'timeframe': '1h', 'signal': 'NEUTRAL', 'confidence': 50}
            ],
            'overall_analysis': {
                "market_phase": "NEUTRAL",
                "confidence": 50,
                "key_insights": ["Данные анализа недоступны"],
                "recommendations": ["Проверьте подключение к API"],
                "risk_level": "MEDIUM",
                "summary": "Базовый анализ: системы работают, данные ограничены"
            },
            'market_phase': 'NEUTRAL',
            'recommendations': ["Проверьте настройки системы"]
        }
