# notifications/__init__.py
"""
Пакет для уведомлений и оповещений

Включает:
- Telegram бот для отправки уведомлений
- Форматтер сообщений
- Система оповещений о торговых сигналах
"""

from .telegram_bot import TelegramNotifier
from .message_formatter import MessageFormatter

__version__ = "1.0.0"
__author__ = "Trading AI System"

# Экспорт основных классов
__all__ = [
    'TelegramNotifier', 
    'MessageFormatter'
]

# Логирование инициализации
import logging
logging.getLogger(__name__).info("📱 Notifications module loaded")
