# utils/config_manager.py
import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class AIConfig:
    """Конфигурация для ИИ анализа"""
    enabled: bool = False
    openai_api_key: Optional[str] = None
    openai_model: str = 'gpt-4'
    analysis_timeout: int = 30
    max_retries: int = 3
    min_analysis_gap: int = 300  # секунд


@dataclass
class TelegramConfig:
    """Конфигурация для Telegram"""
    enabled: bool = False
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    max_message_length: int = 4096
    retry_attempts: int = 3


@dataclass
class TradingConfig:
    """Конфигурация для торговли"""
    enable_ai_validation: bool = False
    min_ai_confidence: int = 60
    require_ai_approval: bool = False
    ai_veto_trades: bool = True  # ИИ может отклонить сделку


class ConfigManager:
    """
    Управляет конфигурацией всех компонентов системы
    """
    
    def __init__(self):
        self._load_config()
        self._validate_config()
        logging.info("⚙️ Конфигурация загружена")
    
    def _load_config(self):
        """Загружает конфигурацию из переменных окружения"""
        
        # AI Configuration
        self.ai = AIConfig(
            enabled=self._get_bool_env('AI_ANALYSIS_ENABLED', False),
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            openai_model=os.getenv('OPENAI_MODEL', 'gpt-4'),
            analysis_timeout=self._get_int_env('AI_ANALYSIS_TIMEOUT', 30),
            max_retries=self._get_int_env('AI_MAX_RETRIES', 3),
            min_analysis_gap=self._get_int_env('AI_MIN_ANALYSIS_GAP', 300)
        )
        
        # Telegram Configuration
        self.telegram = TelegramConfig(
            enabled=self._get_bool_env('TELEGRAM_ENABLED', False),
            bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
            chat_id=os.getenv('TELEGRAM_CHAT_ID'),
            max_message_length=self._get_int_env('TELEGRAM_MAX_MESSAGE_LENGTH', 4096),
            retry_attempts=self._get_int_env('TELEGRAM_RETRY_ATTEMPTS', 3)
        )
        
        # Trading Configuration
        self.trading = TradingConfig(
            enable_ai_validation=self._get_bool_env('ENABLE_AI_VALIDATION', False),
            min_ai_confidence=self._get_int_env('MIN_AI_CONFIDENCE', 60),
            require_ai_approval=self._get_bool_env('REQUIRE_AI_APPROVAL', False),
            ai_veto_trades=self._get_bool_env('AI_VETO_TRADES', True)
        )
    
    def _validate_config(self):
        """Валидирует конфигурацию"""
        errors = []
        
        # Проверка AI конфигурации
        if self.ai.enabled:
            if not self.ai.openai_api_key:
                errors.append("AI включен, но OPENAI_API_KEY не установлен")
            
            if self.ai.analysis_timeout < 10:
                logging.warning("⚠️ Слишком короткий таймаут для ИИ анализа")
        
        # Проверка Telegram конфигурации  
        if self.telegram.enabled:
            if not self.telegram.bot_token:
                errors.append("Telegram включен, но TELEGRAM_BOT_TOKEN не установлен")
            
            if not self.telegram.chat_id:
                errors.append("Telegram включен, но TELEGRAM_CHAT_ID не установлен")
        
        # Проверка торговых настроек
        if self.trading.min_ai_confidence < 0 or self.trading.min_ai_confidence > 100:
            errors.append("MIN_AI_CONFIDENCE должен быть от 0 до 100")
        
        if errors:
            error_message = "❌ Ошибки конфигурации:\n" + "\n".join(f"  • {e}" for e in errors)
            logging.error(error_message)
            raise ValueError(error_message)
        
        # Предупреждения
        if not self.ai.enabled:
            logging.warning("⚠️ ИИ анализ отключен")
        
        if not self.telegram.enabled:
            logging.warning("⚠️ Telegram уведомления отключены")
    
    def _get_bool_env(self, key: str, default: bool = False) -> bool:
        """Получает булево значение из переменной окружения"""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on', 'enabled')
    
    def _get_int_env(self, key: str, default: int) -> int:
        """Получает целое число из переменной окружения"""
        try:
            return int(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            logging.warning(f"⚠️ Некорректное значение для {key}, используется по умолчанию: {default}")
            return default
    
    def _get_float_env(self, key: str, default: float) -> float:
        """Получает число с плавающей точкой из переменной окружения"""
        try:
            return float(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            logging.warning(f"⚠️ Некорректное значение для {key}, используется по умолчанию: {default}")
            return default
    
    @property
    def ai_analysis_enabled(self) -> bool:
        """Проверяет, включен ли ИИ анализ"""
        return self.ai.enabled and bool(self.ai.openai_api_key)
    
    @property
    def telegram_enabled(self) -> bool:
        """Проверяет, включены ли Telegram уведомления"""
        return self.telegram.enabled and bool(self.telegram.bot_token) and bool(self.telegram.chat_id)
    
    def get_summary(self) -> Dict[str, Any]:
        """Возвращает сводку конфигурации"""
        return {
            'ai_analysis': {
                'enabled': self.ai_analysis_enabled,
                'model': self.ai.openai_model if self.ai_analysis_enabled else 'N/A',
                'timeout': self.ai.analysis_timeout
            },
            'telegram': {
                'enabled': self.telegram_enabled,
                'chat_configured': bool(self.telegram.chat_id)
            },
            'trading': {
                'ai_validation': self.trading.enable_ai_validation,
                'min_confidence': self.trading.min_ai_confidence,
                'ai_approval_required': self.trading.require_ai_approval,
                'ai_can_veto': self.trading.ai_veto_trades
            }
        }
    
    def log_summary(self):
        """Логирует сводку конфигурации"""
        summary = self.get_summary()
        
        logging.info("📊 КОНФИГУРАЦИЯ СИСТЕМЫ:")
        logging.info(f"  🤖 ИИ анализ: {'✅ ВКЛЮЧЕН' if summary['ai_analysis']['enabled'] else '❌ ОТКЛЮЧЕН'}")
        if summary['ai_analysis']['enabled']:
            logging.info(f"    • Модель: {summary['ai_analysis']['model']}")
            logging.info(f"    • Таймаут: {summary['ai_analysis']['timeout']}с")
        
        logging.info(f"  📱 Telegram: {'✅ ВКЛЮЧЕН' if summary['telegram']['enabled'] else '❌ ОТКЛЮЧЕН'}")
        
        logging.info(f"  🎯 Торговля:")
        logging.info(f"    • ИИ валидация: {'✅' if summary['trading']['ai_validation'] else '❌'}")
        logging.info(f"    • Минимальная уверенность: {summary['trading']['min_confidence']}%")
        logging.info(f"    • ИИ может отклонить: {'✅' if summary['trading']['ai_can_veto'] else '❌'}")


# Глобальный экземпляр конфигурации
config = ConfigManager()
