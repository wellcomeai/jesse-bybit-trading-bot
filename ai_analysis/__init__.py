# ai_analysis/__init__.py
"""
Пакет для ИИ анализа торговых сигналов

Включает:
- OpenAI анализатор для обработки торговых сигналов
- Сборщик рыночного контекста
- Утилиты для работы с ИИ API
"""

from .openai_analyzer import OpenAIAnalyzer
from .market_context import MarketContextCollector

__version__ = "1.0.0"
__author__ = "Trading AI System"

# Экспорт основных классов
__all__ = [
    'OpenAIAnalyzer',
    'MarketContextCollector'
]

# Логирование инициализации
import logging
logging.getLogger(__name__).info("🤖 AI Analysis module loaded")
