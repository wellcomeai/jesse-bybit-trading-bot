# market_analyzer.py
import asyncio
from typing import Dict, Any, List
from ai_analysis.openai_analyzer import OpenAIAnalyzer
from ai_analysis.market_context import MarketContextCollector
import requests
import jesse.indicators as ta
import numpy as np

class MarketAnalyzer:
    """
    Анализирует рынок по всем стратегиям и дает общую оценку
    """
    
    def __init__(self):
        self.ai_analyzer = OpenAIAnalyzer()
        self.market_context = MarketContextCollector()
        
        # Список активных стратегий
        self.strategies = [
            {'name': 'ActiveScalper', 'timeframe': '5m'},
            {'name': 'BalancedTrader', 'timeframe': '15m'}, 
            {'name': 'QualityTrader', 'timeframe': '1h'}
        ]
    
    async def analyze_all_strategies(self) -> Dict[str, Any]:
        """Анализирует рынок по всем стратегиям"""
        
        # 1. Получаем текущие данные с биржи
        current_data = await self._get_current_market_data()
        
        # 2. Анализируем каждую стратегию
        strategy_analyses = []
        for strategy in self.strategies:
            analysis = await self._analyze_strategy(strategy, current_data)
            strategy_analyses.append(analysis)
        
        # 3. Делаем общий ИИ анализ
        overall_analysis = await self._get_ai_market_overview(strategy_analyses, current_data)
        
        return {
            'timestamp': current_data['timestamp'],
            'price': current_data['price'],
            'strategy_analyses': strategy_analyses,
            'overall_analysis': overall_analysis,
            'market_phase': self._determine_market_phase(strategy_analyses),
            'recommendations': overall_analysis.get('recommendations', [])
        }
    
    async def _get_current_market_data(self) -> Dict[str, Any]:
        """Получает актуальные данные с Bybit"""
        try:
            # Получаем последние свечи
            response = requests.get(
                'https://api-testnet.bybit.com/v5/market/kline',
                params={
                    'category': 'linear',
                    'symbol': 'BTCUSDT',
                    'interval': '5',  # 5 минут
                    'limit': 200
                },
                timeout=10
            )
            
            data = response.json()
            if data['retCode'] == 0:
                candles = data['result']['list']
                
                # Преобразуем в numpy array
                candle_data = []
                for candle in candles:
                    candle_data.append([
                        int(candle[0]),      # timestamp
                        float(candle[1]),    # open
                        float(candle[2]),    # high
                        float(candle[3]),    # low
                        float(candle[4]),    # close
                        float(candle[5])     # volume
                    ])
                
                candles_array = np.array(candle_data)
                
                return {
                    'timestamp': candles[0][0],
                    'price': float(candles[0][4]),  # Текущая цена
                    'candles': candles_array,
                    'volume_24h': sum([float(c[5]) for c in candles[:288]]),  # 24ч объем
                    'change_24h': ((float(candles[0][4]) - float(candles[287][4])) / float(candles[287][4])) * 100
                }
            else:
                raise Exception(f"Bybit API error: {data['retMsg']}")
                
        except Exception as e:
            print(f"Error getting market data: {e}")
            return self._get_mock_data()
    
    def _get_mock_data(self) -> Dict[str, Any]:
        """Заглушка на случай ошибки API"""
        return {
            'timestamp': '1234567890',
            'price': 45000.0,
            'candles': np.zeros((200, 6)),
            'volume_24h': 1000000,
            'change_24h': 2.5
        }
    
    async def _analyze_strategy(self, strategy: Dict, market_data: Dict) -> Dict[str, Any]:
        """Анализирует рынок с точки зрения конкретной стратегии"""
        
        candles = market_data['candles']
        
        # Рассчитываем индикаторы для стратегии
        if strategy['name'] == 'ActiveScalper':
            indicators = self._calculate_scalper_indicators(candles)
        elif strategy['name'] == 'BalancedTrader':
            indicators = self._calculate_balanced_indicators(candles)
        elif strategy['name'] == 'QualityTrader':
            indicators = self._calculate_quality_indicators(candles)
        else:
            indicators = {}
        
        # Определяем сигнал стратегии
        signal = self._get_strategy_signal(strategy['name'], indicators, candles)
        
        return {
            'strategy': strategy['name'],
            'timeframe': strategy['timeframe'],
            'indicators': indicators,
            'signal': signal,
            'confidence': self._calculate_signal_confidence(signal, indicators)
        }
    
    def _calculate_scalper_indicators(self, candles: np.ndarray) -> Dict:
        """Индикаторы для ActiveScalper"""
        return {
            'ema8': ta.ema(candles, period=8),
            'ema13': ta.ema(candles, period=13),
            'ema21': ta.ema(candles, period=21),
            'rsi': ta.rsi(candles, period=7),
            'bb_upper': ta.bollinger_bands(candles, period=20, devup=2)[0],
            'bb_lower': ta.bollinger_bands(candles, period=20, devup=2)[2]
        }
    
    def _calculate_balanced_indicators(self, candles: np.ndarray) -> Dict:
        """Индикаторы для BalancedTrader"""
        return {
            'ema9': ta.ema(candles, period=9),
            'ema21': ta.ema(candles, period=21),
            'rsi': ta.rsi(candles, period=14),
            'atr': ta.atr(candles, period=14)
        }
    
    def _calculate_quality_indicators(self, candles: np.ndarray) -> Dict:
        """Индикаторы для QualityTrader"""
        return {
            'ema12': ta.ema(candles, period=12),
            'ema26': ta.ema(candles, period=26),
            'ema50': ta.ema(candles, period=50),
            'rsi': ta.rsi(candles, period=14)
        }
    
    def _get_strategy_signal(self, strategy_name: str, indicators: Dict, candles: np.ndarray) -> str:
        """Определяет сигнал стратегии"""
        current_price = candles[-1, 4]  # Текущая цена
        
        if strategy_name == 'ActiveScalper':
            ema8, ema13, ema21 = indicators['ema8'], indicators['ema13'], indicators['ema21']
            if current_price > ema8 > ema13 > ema21:
                return 'STRONG_BUY'
            elif current_price > ema21:
                return 'BUY'
            elif current_price < ema8 < ema13 < ema21:
                return 'STRONG_SELL'
            elif current_price < ema21:
                return 'SELL'
            else:
                return 'NEUTRAL'
        
        # Аналогично для других стратегий...
        return 'NEUTRAL'
    
    def _calculate_signal_confidence(self, signal: str, indicators: Dict) -> int:
        """Рассчитывает уверенность в сигнале (0-100)"""
        if signal in ['STRONG_BUY', 'STRONG_SELL']:
            return 80
        elif signal in ['BUY', 'SELL']:
            return 60
        else:
            return 30
    
    async def _get_ai_market_overview(self, strategy_analyses: List, market_data: Dict) -> Dict[str, Any]:
        """Получает общий анализ рынка от ИИ"""
        
        # Подготавливаем данные для ИИ
        ai_prompt = self._build_market_analysis_prompt(strategy_analyses, market_data)
        
        # Отправляем в OpenAI
        ai_response = await self.ai_analyzer.client.chat.completions.create(
            model=self.ai_analyzer.model,
            messages=[
                {
                    "role": "system", 
                    "content": self._get_market_analysis_system_prompt()
                },
                {
                    "role": "user",
                    "content": ai_prompt
                }
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        # Парсим ответ
        return self._parse_market_analysis(ai_response.choices[0].message.content)
    
    def _get_market_analysis_system_prompt(self) -> str:
        """Системный промпт для анализа рынка"""
        return """Ты - эксперт по анализу криптовалютных рынков.

ЗАДАЧА: Проанализировать общее состояние рынка BTC на основе данных от нескольких торговых стратегий.

ФОРМАТ ОТВЕТА (строго JSON):
{
    "market_phase": "BULL_TREND|BEAR_TREND|SIDEWAYS|VOLATILE",
    "confidence": 0-100,
    "key_insights": ["инсайт1", "инсайт2", "инсайт3"],
    "recommendations": ["рекомендация1", "рекомендация2"],
    "risk_level": "LOW|MEDIUM|HIGH",
    "summary": "краткая сводка в 2-3 предложения"
}

Анализируй объективно, учитывая все данные."""
    
    def _build_market_analysis_prompt(self, strategy_analyses: List, market_data: Dict) -> str:
        """Строит промпт для анализа рынка"""
        
        prompt = f"""АНАЛИЗ РЫНКА BTC:

=== ТЕКУЩИЕ ДАННЫЕ ===
Цена: ${market_data['price']:,.2f}
Изменение 24ч: {market_data['change_24h']:+.2f}%
Объем 24ч: {market_data['volume_24h']:,.0f}

=== АНАЛИЗ ПО СТРАТЕГИЯМ ==="""

        for analysis in strategy_analyses:
            prompt += f"""

{analysis['strategy']} ({analysis['timeframe']}):
- Сигнал: {analysis['signal']}
- Уверенность: {analysis['confidence']}%
- Ключевые индикаторы: {list(analysis['indicators'].keys())}"""

        prompt += f"""

ПРОАНАЛИЗИРУЙ общее состояние рынка и дай рекомендации."""
        
        return prompt
    
    def _parse_market_analysis(self, response_text: str) -> Dict[str, Any]:
        """Парсит ответ ИИ о состоянии рынка"""
        try:
            import json
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            json_str = response_text[start:end]
            return json.loads(json_str)
        except:
            return {
                "market_phase": "UNKNOWN",
                "confidence": 50,
                "key_insights": ["Ошибка анализа"],
                "recommendations": ["Требуется ручная проверка"],
                "risk_level": "MEDIUM",
                "summary": "Не удалось проанализировать рынок"
            }
    
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
