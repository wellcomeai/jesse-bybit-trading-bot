# ai_analysis/openai_analyzer.py
import openai
import json
import os
from typing import Dict, Any, Optional
import asyncio
from datetime import datetime
import logging


class OpenAIAnalyzer:
    """
    Анализатор торговых сигналов через OpenAI API
    """
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=os.getenv('OPENAI_API_KEY')
        )
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4')
        self.max_retries = 3
        self.timeout = 30
        
        # Проверяем наличие API ключа
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY не найден в переменных окружения!")
        
        logging.info(f"🤖 OpenAI анализатор инициализирован с моделью: {self.model}")
    
    async def analyze_signal(self, signal_data: Dict[str, Any], market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Анализирует торговый сигнал через OpenAI
        
        Args:
            signal_data: Данные о сигнале стратегии
            market_data: Рыночный контекст
            
        Returns:
            Dict с анализом ИИ или None при ошибке
        """
        try:
            prompt = self._build_analysis_prompt(signal_data, market_data)
            
            for attempt in range(self.max_retries):
                try:
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "system",
                                "content": self._get_system_prompt()
                            },
                            {
                                "role": "user", 
                                "content": prompt
                            }
                        ],
                        temperature=0.3,  # Низкая температура для более точных ответов
                        max_tokens=1500,
                        timeout=self.timeout
                    )
                    
                    analysis_text = response.choices[0].message.content
                    parsed_analysis = self._parse_ai_response(analysis_text)
                    
                    logging.info(f"✅ ИИ анализ получен (попытка {attempt + 1})")
                    return parsed_analysis
                    
                except openai.RateLimitError:
                    logging.warning(f"⏳ Лимит запросов OpenAI, ожидание... (попытка {attempt + 1})")
                    await asyncio.sleep(2 ** attempt)  # Экспоненциальная задержка
                    
                except openai.APITimeoutError:
                    logging.warning(f"⏰ Таймаут OpenAI API (попытка {attempt + 1})")
                    if attempt == self.max_retries - 1:
                        raise
                    
                except Exception as e:
                    logging.error(f"❌ Ошибка OpenAI API (попытка {attempt + 1}): {e}")
                    if attempt == self.max_retries - 1:
                        raise
                    await asyncio.sleep(1)
            
            return None
            
        except Exception as e:
            logging.error(f"❌ Критическая ошибка ИИ анализа: {e}")
            return None
    
    def _get_system_prompt(self) -> str:
        """
        Системный промпт для ИИ анализатора
        """
        return """Ты - эксперт по техническому анализу криптовалютных рынков с 10+ лет опыта.

ТВОЯ ЗАДАЧА:
Проанализировать торговый сигнал и дать объективную оценку с аргументацией.

ФОРМАТ ОТВЕТА (строго JSON):
{
    "recommendation": "BUY|SELL|HOLD|AVOID",
    "confidence": 0-100,
    "risk_level": "LOW|MEDIUM|HIGH",
    "key_factors": {
        "bullish": ["фактор1", "фактор2"],
        "bearish": ["фактор1", "фактор2"]
    },
    "market_analysis": "краткий анализ рыночной ситуации",
    "strategy_assessment": "оценка качества сигнала стратегии",
    "risk_warnings": ["предупреждение1", "предупреждение2"],
    "target_zones": {
        "entry_optimal": "цена входа",
        "stop_loss": "стоп-лосс", 
        "take_profit_1": "первая цель",
        "take_profit_2": "вторая цель"
    },
    "summary": "итоговое заключение в 2-3 предложения"
}

ПРИНЦИПЫ АНАЛИЗА:
- Объективность выше всего
- Учитывай весь рыночный контекст
- Не бойся говорить AVOID при плохих условиях
- Confidence = реальная уверенность в сигнале
- Risk_level основан на волатильности и неопределенности"""

    def _build_analysis_prompt(self, signal_data: Dict[str, Any], market_data: Dict[str, Any]) -> str:
        """
        Строит промпт для анализа конкретного сигнала
        """
        # Форматируем данные о сигнале
        strategy = signal_data.get('strategy', 'Unknown')
        signal_type = signal_data.get('signal_type', 'Unknown')
        reason = signal_data.get('reason', 'Unknown')
        price = signal_data.get('price', 0)
        symbol = signal_data.get('symbol', 'Unknown')
        timeframe = signal_data.get('timeframe', 'Unknown')
        
        # Индикаторы
        indicators = signal_data.get('indicators', {})
        
        # Последние свечи
        recent_candles = signal_data.get('candles_data', {}).get('recent_candles', [])
        
        # Рыночный контекст
        market_sentiment = market_data.get('sentiment', 'NEUTRAL')
        volatility = market_data.get('volatility', 'MEDIUM')
        
        prompt = f"""АНАЛИЗ ТОРГОВОГО СИГНАЛА:

=== ОСНОВНЫЕ ДАННЫЕ ===
Стратегия: {strategy}
Сигнал: {signal_type} на {symbol}
Таймфрейм: {timeframe}
Текущая цена: ${price:,.2f}
Причина сигнала: {reason}
Время: {datetime.fromtimestamp(signal_data.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')}

=== ТЕХНИЧЕСКИЕ ИНДИКАТОРЫ ==="""

        # Добавляем индикаторы
        for indicator, value in indicators.items():
            if isinstance(value, (int, float)):
                prompt += f"\n{indicator.upper()}: {value:.2f}"
        
        prompt += f"\n\n=== РЫНОЧНЫЕ УСЛОВИЯ ==="
        prompt += f"\nНастроение рынка: {market_sentiment}"
        prompt += f"\nВолатильность: {volatility}"
        
        # Добавляем данные о последних свечах (краткий анализ)
        if recent_candles:
            prompt += f"\n\n=== ПОСЛЕДНИЕ {len(recent_candles)} СВЕЧЕЙ ==="
            
            # Берем только последние 5 свечей для краткости
            for i, candle in enumerate(recent_candles[-5:]):
                open_price = candle.get('open', 0)
                close_price = candle.get('close', 0)
                high_price = candle.get('high', 0)
                low_price = candle.get('low', 0)
                volume = candle.get('volume', 0)
                
                change = ((close_price - open_price) / open_price * 100) if open_price > 0 else 0
                candle_type = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"
                
                prompt += f"\n{candle_type} #{i+1}: O${open_price:.2f} H${high_price:.2f} L${low_price:.2f} C${close_price:.2f} ({change:+.2f}%) Vol:{volume:.0f}"
        
        prompt += f"\n\n=== ДОПОЛНИТЕЛЬНЫЙ КОНТЕКСТ ==="
        additional_data = signal_data.get('additional_data', {})
        if additional_data:
            for key, value in additional_data.items():
                prompt += f"\n{key}: {value}"
        
        prompt += f"\n\nПРОВЕДИ ПОЛНЫЙ АНАЛИЗ ЭТОГО СИГНАЛА И ВЕРНИ РЕЗУЛЬТАТ В ФОРМАТЕ JSON!"
        
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """
        Парсит ответ ИИ в структурированный формат
        """
        try:
            # Пытаемся найти JSON в ответе
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                # Если JSON не найден, создаем базовую структуру
                return self._create_fallback_response(response_text)
            
            json_text = response_text[start_idx:end_idx + 1]
            parsed = json.loads(json_text)
            
            # Валидация обязательных полей
            required_fields = ['recommendation', 'confidence', 'risk_level', 'summary']
            for field in required_fields:
                if field not in parsed:
                    parsed[field] = self._get_default_value(field)
            
            # Нормализация значений
            parsed = self._normalize_response(parsed)
            
            return parsed
            
        except json.JSONDecodeError as e:
            logging.warning(f"⚠️ Ошибка парсинга JSON от ИИ: {e}")
            return self._create_fallback_response(response_text)
        
        except Exception as e:
            logging.error(f"❌ Ошибка обработки ответа ИИ: {e}")
            return self._create_fallback_response(response_text)
    
    def _create_fallback_response(self, original_text: str) -> Dict[str, Any]:
        """
        Создает запасной ответ если не удалось парсить JSON
        """
        return {
            "recommendation": "HOLD",
            "confidence": 50,
            "risk_level": "MEDIUM",
            "key_factors": {
                "bullish": [],
                "bearish": []
            },
            "market_analysis": "Анализ недоступен",
            "strategy_assessment": "Требует ручной проверки",
            "risk_warnings": ["Ошибка автоматического анализа"],
            "target_zones": {},
            "summary": "ИИ анализ завершился с ошибкой. Требуется ручная проверка сигнала.",
            "raw_response": original_text[:500]  # Первые 500 символов для отладки
        }
    
    def _get_default_value(self, field: str) -> Any:
        """
        Возвращает значение по умолчанию для поля
        """
        defaults = {
            "recommendation": "HOLD",
            "confidence": 50,
            "risk_level": "MEDIUM",
            "summary": "Анализ требует уточнения",
            "key_factors": {"bullish": [], "bearish": []},
            "market_analysis": "Не определен",
            "strategy_assessment": "Не определена",
            "risk_warnings": [],
            "target_zones": {}
        }
        return defaults.get(field, "Unknown")
    
    def _normalize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Нормализует значения в ответе ИИ
        """
        # Нормализация recommendation
        if response.get('recommendation'):
            rec = str(response['recommendation']).upper()
            if rec not in ['BUY', 'SELL', 'HOLD', 'AVOID']:
                response['recommendation'] = 'HOLD'
        
        # Нормализация confidence
        try:
            confidence = int(response.get('confidence', 50))
            response['confidence'] = max(0, min(100, confidence))
        except (ValueError, TypeError):
            response['confidence'] = 50
        
        # Нормализация risk_level
        if response.get('risk_level'):
            risk = str(response['risk_level']).upper()
            if risk not in ['LOW', 'MEDIUM', 'HIGH']:
                response['risk_level'] = 'MEDIUM'
        
        return response
