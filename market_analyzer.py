# market_analyzer.py - ИСПРАВЛЕННАЯ ФИНАЛЬНАЯ ВЕРСИЯ
import asyncio
from typing import Dict, Any, List
import requests
import numpy as np
from datetime import datetime
import logging
import traceback
import os

class MarketAnalyzer:
    """
    ИСПРАВЛЕННЫЙ анализатор рынка с официальной OpenAI библиотекой
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Список активных стратегий
        self.strategies = [
            {'name': 'ActiveScalper', 'timeframe': '5m'},
            {'name': 'BalancedTrader', 'timeframe': '15m'}, 
            {'name': 'QualityTrader', 'timeframe': '1h'}
        ]
        
        self.logger.info("🏗️ MarketAnalyzer инициализирован (с официальной OpenAI библиотекой)")

    async def analyze_all_strategies(self) -> Dict[str, Any]:
        """ИСПРАВЛЕНО: анализ с официальной OpenAI библиотекой"""
        try:
            self.logger.info("🚀 === НАЧАЛО АНАЛИЗА ВСЕХ СТРАТЕГИЙ ===")
            
            # 1. Получаем данные с биржи
            self.logger.info("📊 ШАГ 1: Получение данных с Bybit")
            current_data = await self._get_current_market_data_safe()
            
            if not current_data or current_data.get('price', 0) == 0:
                raise Exception("Не удалось получить корректные данные с биржи Bybit")
            
            self.logger.info(f"✅ Данные с биржи получены: цена ${current_data['price']:,.2f}")
            
            # 2. Анализируем каждую стратегию
            self.logger.info("🎯 ШАГ 2: Анализ стратегий")
            strategy_analyses = []
            
            for strategy in self.strategies:
                self.logger.info(f"  Анализируем {strategy['name']}...")
                analysis = self._analyze_strategy_sync(strategy, current_data)
                strategy_analyses.append(analysis)
                self.logger.info(f"  ✅ {strategy['name']}: {analysis['signal']} ({analysis['confidence']}%)")
            
            # 3. ИИ анализ (ИСПРАВЛЕНО: с официальной OpenAI библиотекой!)
            self.logger.info("🧠 ШАГ 3: Запуск ИИ анализа (OpenAI)")
            overall_analysis = await self._get_ai_market_overview_strict(strategy_analyses, current_data)
            
            if not overall_analysis or 'error' in overall_analysis:
                error_msg = overall_analysis.get('error', 'Неизвестная ошибка ИИ анализа') if overall_analysis else 'ИИ анализ вернул пустой результат'
                raise Exception(f"Ошибка ИИ анализа: {error_msg}")
            
            self.logger.info(f"✅ ИИ анализ завершен: {overall_analysis.get('market_phase', 'UNKNOWN')}")
            
            # 4. Формируем результат
            result = {
                'timestamp': current_data['timestamp'],
                'price': current_data['price'],
                'strategy_analyses': strategy_analyses,
                'overall_analysis': overall_analysis,
                'market_phase': self._determine_market_phase(strategy_analyses),
                'recommendations': overall_analysis.get('recommendations', []),
                'data_source': 'REAL_API_DATA',
                'analysis_type': 'FULL_AI_ANALYSIS'
            }
            
            self.logger.info("🎉 === АНАЛИЗ ЗАВЕРШЕН УСПЕШНО ===")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ ОШИБКА анализа стратегий: {e}")
            self.logger.error(f"Полный traceback: {traceback.format_exc()}")
            raise Exception(f"Критическая ошибка MarketAnalyzer: {e}")

    async def _get_current_market_data_safe(self) -> Dict[str, Any]:
        """Получает данные с Bybit с детальным логированием"""
        try:
            self.logger.info("🌐 Подключаюсь к Bybit API...")
            
            response = requests.get(
                'https://api-testnet.bybit.com/v5/market/kline',
                params={
                    'category': 'linear',
                    'symbol': 'BTCUSDT',
                    'interval': '5',
                    'limit': 50
                },
                timeout=15
            )
            
            self.logger.info(f"📡 Ответ Bybit API: статус {response.status_code}")
            
            if response.status_code != 200:
                raise Exception(f"Bybit API вернул статус {response.status_code}")
            
            data = response.json()
            
            if data.get('retCode') != 0:
                error_msg = data.get('retMsg', 'Неизвестная ошибка Bybit API')
                raise Exception(f"Ошибка Bybit API: {error_msg} (код: {data.get('retCode')})")
            
            candles = data['result']['list']
            self.logger.info(f"📊 Получено {len(candles)} свечей")
            
            if not candles:
                raise Exception("Bybit API вернул пустой список свечей")
            
            # Преобразуем данные
            candle_data = []
            for i, candle in enumerate(candles[:20]):
                try:
                    candle_data.append([
                        int(candle[0]),      # timestamp
                        float(candle[1]),    # open
                        float(candle[2]),    # high
                        float(candle[3]),    # low
                        float(candle[4]),    # close
                        float(candle[5])     # volume
                    ])
                except (ValueError, IndexError) as e:
                    self.logger.warning(f"⚠️ Ошибка обработки свечи {i}: {e}")
            
            if not candle_data:
                raise Exception("Не удалось обработать ни одной свечи из Bybit")
            
            candles_array = np.array(candle_data)
            current_price = float(candles[0][4])
            
            # Рассчитываем изменение за 24ч
            if len(candles) >= 10:
                old_price = float(candles[10][4])
                change_24h = ((current_price - old_price) / old_price) * 100
            else:
                change_24h = 0
            
            result = {
                'timestamp': candles[0][0],
                'price': current_price,
                'candles': candles_array,
                'volume_24h': sum([float(c[5]) for c in candles[:20]]),
                'change_24h': change_24h,
                'data_source': 'BYBIT_TESTNET_API'
            }
            
            self.logger.info(f"✅ Данные обработаны: цена=${current_price:,.2f}, изм.24ч={change_24h:+.2f}%")
            return result
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения данных с Bybit: {e}")
            raise Exception(f"Не удалось получить данные с Bybit: {e}")

    def _analyze_strategy_sync(self, strategy: Dict, market_data: Dict) -> Dict[str, Any]:
        """Анализирует рынок с точки зрения конкретной стратегии"""
        
        candles = market_data['candles']
        current_price = market_data['price']
        
        # Простые сигналы на основе данных
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
        
        recent_closes = candles[-5:, 4]
        avg_price = np.mean(recent_closes)
        
        if price > avg_price * 1.002:
            return 'BUY'
        elif price < avg_price * 0.998:
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
        if volume_24h > 800000:
            if price > 43000:
                return 'STRONG_BUY'
            else:
                return 'BUY'
        elif volume_24h < 300000:
            return 'NEUTRAL'
        else:
            return 'HOLD'

    async def _get_ai_market_overview_strict(self, strategy_analyses: List, market_data: Dict) -> Dict[str, Any]:
        """ИСПРАВЛЕНО: Строгий ИИ анализ с официальной OpenAI библиотекой"""
        try:
            self.logger.info("🧠 Запуск ИИ анализа через официальную OpenAI библиотеку...")
            
            # Проверяем наличие OpenAI ключа
            openai_key = os.getenv('OPENAI_API_KEY')
            if not openai_key:
                raise Exception("OPENAI_API_KEY не найден в переменных окружения")
            
            self.logger.info(f"🔑 OpenAI ключ найден (длина: {len(openai_key)})")
            
            # ИСПРАВЛЕНИЕ: Используем официальную OpenAI библиотеку вместо aiohttp
            import openai
            
            # Создаем асинхронного клиента
            client = openai.AsyncOpenAI(api_key=openai_key)
            
            prompt = self._build_market_analysis_prompt(strategy_analyses, market_data)
            self.logger.info(f"📝 Промпт подготовлен (длина: {len(prompt)} символов)")
            
            model = os.getenv('OPENAI_MODEL', 'gpt-4')
            self.logger.info(f"🤖 Отправляю запрос к OpenAI API (модель: {model})")
            
            # Делаем запрос через официальную библиотеку
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system", 
                        "content": self._get_market_analysis_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            self.logger.info("✅ Ответ OpenAI получен через официальную библиотеку!")
            
            # Получаем текст ответа
            ai_text = response.choices[0].message.content
            self.logger.info(f"📄 Получен текст от GPT (длина: {len(ai_text)})")
            
            # Парсим ответ
            parsed_analysis = self._parse_ai_response_strict(ai_text)
            
            if not parsed_analysis or 'error' in parsed_analysis:
                raise Exception(f"Не удалось корректно распарсить ответ GPT: {parsed_analysis}")
            
            # Добавляем метки что это реальный ИИ анализ
            parsed_analysis['ai_source'] = 'OPENAI_GPT'
            parsed_analysis['analysis_type'] = 'REAL_AI'
            parsed_analysis['timestamp'] = datetime.now().isoformat()
            
            self.logger.info("✅ ИИ анализ успешно завершен и распарсен")
            return parsed_analysis
                    
        except Exception as e:
            self.logger.error(f"❌ КРИТИЧЕСКАЯ ошибка ИИ анализа: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Возвращаем объект с ошибкой
            return {
                'error': str(e),
                'error_type': 'AI_ANALYSIS_FAILED',
                'timestamp': datetime.now().isoformat()
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
Источник данных: Bybit Testnet API

=== АНАЛИЗ ПО СТРАТЕГИЯМ ==="""

        for analysis in strategy_analyses:
            prompt += f"""

{analysis['strategy']} ({analysis['timeframe']}):
- Сигнал: {analysis['signal']}
- Уверенность: {analysis['confidence']}%"""

        prompt += f"""

ЗАДАЧА: Проанализируй общее состояние рынка BTC на основе этих данных.

ВАЖНО: Ответь СТРОГО в формате JSON. Не добавляй никаких комментариев вне JSON.
"""
        
        return prompt

    def _get_market_analysis_system_prompt(self) -> str:
        """Системный промпт для анализа рынка"""
        return """Ты - эксперт по анализу криптовалютных рынков.

ЗАДАЧА: Проанализировать рынок BTC на основе данных от торговых стратегий.

ФОРМАТ ОТВЕТА (строго JSON):
{
    "market_phase": "BULLISH|BEARISH|NEUTRAL|VOLATILE",
    "confidence": 0-100,
    "key_insights": ["инсайт1", "инсайт2", "инсайт3"],
    "recommendations": ["рекомендация1", "рекомендация2", "рекомендация3"],
    "risk_level": "LOW|MEDIUM|HIGH",
    "summary": "краткая сводка в 2-3 предложения"
}

НЕ добавляй никакой текст вне JSON. Отвечай только валидным JSON."""

    def _parse_ai_response_strict(self, response_text: str) -> Dict[str, Any]:
        """Строгий парсинг без fallback'ов"""
        try:
            import json
            
            self.logger.info("🔍 Начинаю парсинг ответа GPT...")
            
            # Ищем JSON в тексте
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                raise ValueError(f"JSON не найден в ответе GPT")
            
            json_text = response_text[start_idx:end_idx + 1]
            parsed = json.loads(json_text)
            
            # Валидация обязательных полей
            required_fields = ['market_phase', 'confidence', 'summary']
            missing_fields = [field for field in required_fields if field not in parsed]
            
            if missing_fields:
                raise ValueError(f"Отсутствуют обязательные поля в ответе GPT: {missing_fields}")
            
            # Валидация значений
            if not isinstance(parsed.get('confidence'), (int, float)) or not (0 <= parsed['confidence'] <= 100):
                raise ValueError(f"Некорректное значение confidence: {parsed.get('confidence')}")
            
            self.logger.info("✅ Валидация ответа GPT прошла успешно")
            return parsed
                
        except json.JSONDecodeError as e:
            error_msg = f"Ошибка парсинга JSON от GPT: {e}"
            self.logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)
        
        except Exception as e:
            error_msg = f"Ошибка обработки ответа GPT: {e}"
            self.logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)

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
