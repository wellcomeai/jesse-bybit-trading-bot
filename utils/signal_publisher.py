# utils/signal_publisher.py
"""
Публикатор торговых сигналов для интеграции с внешними системами
Может использоваться для отправки сигналов в очереди сообщений, webhooks и т.д.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import aiohttp


class SignalPublisher:
    """
    Публикует торговые сигналы во внешние системы
    """
    
    def __init__(self):
        self.webhooks: List[str] = []
        self.session: Optional[aiohttp.ClientSession] = None
        self.enabled = False
        
        # Загрузка настроек из переменных окружения
        self._load_config()
        
        if self.enabled:
            logging.info("📡 Signal Publisher инициализирован")
    
    def _load_config(self):
        """Загружает конфигурацию из переменных окружения"""
        import os
        
        # Webhook URLs (разделенные запятой)
        webhook_urls = os.getenv('SIGNAL_WEBHOOKS', '')
        if webhook_urls:
            self.webhooks = [url.strip() for url in webhook_urls.split(',') if url.strip()]
        
        self.enabled = len(self.webhooks) > 0
        
        # Настройки для отправки
        self.timeout = int(os.getenv('SIGNAL_TIMEOUT', '10'))
        self.max_retries = int(os.getenv('SIGNAL_MAX_RETRIES', '3'))
    
    async def publish_signal(self, signal_data: Dict[str, Any], ai_analysis: Optional[Dict[str, Any]] = None) -> bool:
        """
        Публикует торговый сигнал
        
        Args:
            signal_data: Данные о торговом сигнале
            ai_analysis: Результат ИИ анализа (опционально)
            
        Returns:
            True если сигнал опубликован успешно
        """
        if not self.enabled:
            return True  # Не ошибка, просто отключено
        
        try:
            # Подготавливаем данные для отправки
            payload = self._prepare_payload(signal_data, ai_analysis)
            
            # Отправляем во все настроенные webhooks
            success_count = 0
            
            for webhook_url in self.webhooks:
                if await self._send_to_webhook(webhook_url, payload):
                    success_count += 1
            
            # Считаем успешным если хотя бы один webhook сработал
            success = success_count > 0
            
            if success:
                logging.info(f"📡 Сигнал опубликован успешно ({success_count}/{len(self.webhooks)} webhooks)")
            else:
                logging.error("❌ Не удалось опубликовать сигнал ни в один webhook")
            
            return success
            
        except Exception as e:
            logging.error(f"❌ Ошибка публикации сигнала: {e}")
            return False
    
    def _prepare_payload(self, signal_data: Dict[str, Any], ai_analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Подготавливает данные для отправки
        """
        payload = {
            'timestamp': datetime.now().isoformat(),
            'signal': {
                'strategy': signal_data.get('strategy', 'Unknown'),
                'type': signal_data.get('signal_type', 'Unknown'),
                'symbol': signal_data.get('symbol', 'Unknown'),
                'price': signal_data.get('price', 0),
                'exchange': signal_data.get('exchange', 'Unknown'),
                'timeframe': signal_data.get('timeframe', 'Unknown'),
                'reason': signal_data.get('reason', 'Unknown')
            },
            'indicators': signal_data.get('indicators', {}),
            'source': 'AI_Trading_Bot',
            'version': '1.0.0'
        }
        
        # Добавляем ИИ анализ если есть
        if ai_analysis:
            payload['ai_analysis'] = {
                'recommendation': ai_analysis.get('recommendation', 'UNKNOWN'),
                'confidence': ai_analysis.get('confidence', 0),
                'risk_level': ai_analysis.get('risk_level', 'UNKNOWN'),
                'summary': ai_analysis.get('summary', ''),
                'key_factors': ai_analysis.get('key_factors', {}),
                'target_zones': ai_analysis.get('target_zones', {})
            }
        
        return payload
    
    async def _send_to_webhook(self, webhook_url: str, payload: Dict[str, Any]) -> bool:
        """
        Отправляет данные в конкретный webhook
        """
        for attempt in range(self.max_retries):
            try:
                if not self.session:
                    self.session = aiohttp.ClientSession()
                
                async with self.session.post(
                    webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'AI-Trading-Bot/1.0'
                    }
                ) as response:
                    
                    if response.status == 200:
                        logging.debug(f"✅ Webhook успешно: {webhook_url}")
                        return True
                    else:
                        logging.warning(f"⚠️ Webhook вернул {response.status}: {webhook_url}")
                        
            except asyncio.TimeoutError:
                logging.warning(f"⏰ Timeout webhook (попытка {attempt + 1}): {webhook_url}")
                
            except Exception as e:
                logging.warning(f"❌ Ошибка webhook (попытка {attempt + 1}): {webhook_url} - {e}")
            
            # Задержка перед повторной попыткой
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Экспоненциальная задержка
        
        return False
    
    async def publish_trade_result(self, trade_result: Dict[str, Any]) -> bool:
        """
        Публикует результат сделки
        """
        if not self.enabled:
            return True
        
        try:
            payload = {
                'timestamp': datetime.now().isoformat(),
                'trade_result': {
                    'symbol': trade_result.get('symbol', 'Unknown'),
                    'strategy': trade_result.get('strategy', 'Unknown'),
                    'entry_price': trade_result.get('entry_price', 0),
                    'exit_price': trade_result.get('exit_price', 0),
                    'pnl': trade_result.get('pnl', 0),
                    'duration': trade_result.get('duration', 0),
                    'result': 'PROFIT' if trade_result.get('pnl', 0) > 0 else 'LOSS'
                },
                'source': 'AI_Trading_Bot',
                'version': '1.0.0'
            }
            
            success_count = 0
            for webhook_url in self.webhooks:
                if await self._send_to_webhook(webhook_url, payload):
                    success_count += 1
            
            return success_count > 0
            
        except Exception as e:
            logging.error(f"❌ Ошибка публикации результата сделки: {e}")
            return False
    
    async def close(self):
        """
        Закрывает соединения
        """
        if self.session:
            await self.session.close()
            self.session = None
    
    async def __aenter__(self):
        """Асинхронный контекстный менеджер"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие при выходе из контекста"""
        await self.close()


# Глобальный экземпляр
signal_publisher = SignalPublisher()
