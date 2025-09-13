# notifications/message_formatter.py
"""
Форматирует сообщения для отправки в Telegram
"""
from datetime import datetime
from typing import Dict, Any


class MessageFormatter:
    """
    Форматирует сообщения для отправки в Telegram
    """
    
    def __init__(self):
        self.max_message_length = 4096  # Лимит Telegram
    
    def format_analysis_message(self, signal_data: Dict[str, Any], ai_analysis: Dict[str, Any]) -> str:
        """
        Форматирует сообщение с результатами ИИ анализа
        """
        # Получаем данные
        strategy = signal_data.get('strategy', 'Unknown')
        signal_type = signal_data.get('signal_type', 'Unknown')
        symbol = signal_data.get('symbol', 'Unknown')
        price = signal_data.get('price', 0)
        
        # Результаты ИИ
        recommendation = ai_analysis.get('recommendation', 'UNKNOWN')
        confidence = ai_analysis.get('confidence', 0)
        risk_level = ai_analysis.get('risk_level', 'UNKNOWN')
        summary = ai_analysis.get('summary', 'Анализ недоступен')
        
        # Эмодзи для рекомендаций
        rec_emoji = {
            'BUY': '🚀',
            'SELL': '📉', 
            'HOLD': '⏳',
            'AVOID': '⛔'
        }.get(recommendation, '❓')
        
        # Эмодзи для сигнала
        signal_emoji = '🟢' if signal_type == 'LONG' else '🔴' if signal_type == 'SHORT' else '🟡'
        
        # Эмодзи для риска
        risk_emoji = {
            'LOW': '🟢',
            'MEDIUM': '🟡',
            'HIGH': '🔴'
        }.get(risk_level, '⚪')
        
        # Основное сообщение
        message = f"🤖 <b>ИИ АНАЛИЗ СИГНАЛА</b>\n\n"
        
        message += f"{signal_emoji} <b>{signal_type}</b> • {symbol}\n"
        message += f"🎯 Стратегия: <code>{strategy}</code>\n"
        message += f"💰 Цена: <b>${price:,.2f}</b>\n"
        message += f"⏰ Время: {datetime.fromtimestamp(signal_data.get('timestamp', 0)).strftime('%H:%M:%S')}\n\n"
        
        message += f"🧠 <b>ИИ РЕКОМЕНДАЦИЯ</b>\n"
        message += f"{rec_emoji} <b>{recommendation}</b>\n"
        message += f"📊 Уверенность: <b>{confidence}%</b>\n"
        message += f"{risk_emoji} Риск: <b>{risk_level}</b>\n\n"
        
        # Ключевые факторы
        key_factors = ai_analysis.get('key_factors', {})
        bullish = key_factors.get('bullish', [])
        bearish = key_factors.get('bearish', [])
        
        if bullish or bearish:
            message += f"📈 <b>АНАЛИЗ ФАКТОРОВ</b>\n"
            
            if bullish:
                message += f"🟢 <b>За:</b>\n"
                for factor in bullish[:3]:  # Максимум 3 фактора
                    message += f"  • {factor}\n"
            
            if bearish:
                message += f"🔴 <b>Против:</b>\n"
                for factor in bearish[:3]:  # Максимум 3 фактора
                    message += f"  • {factor}\n"
            
            message += "\n"
        
        # Целевые уровни
        target_zones = ai_analysis.get('target_zones', {})
        if target_zones:
            message += f"🎯 <b>ЦЕЛЕВЫЕ УРОВНИ</b>\n"
            
            if 'stop_loss' in target_zones:
                message += f"🛑 Stop Loss: <code>{target_zones['stop_loss']}</code>\n"
            if 'take_profit_1' in target_zones:
                message += f"🎯 Take Profit 1: <code>{target_zones['take_profit_1']}</code>\n"
            if 'take_profit_2' in target_zones:
                message += f"🎯 Take Profit 2: <code>{target_zones['take_profit_2']}</code>\n"
            
            message += "\n"
        
        # Предупреждения о рисках
        risk_warnings = ai_analysis.get('risk_warnings', [])
        if risk_warnings:
            message += f"⚠️ <b>ПРЕДУПРЕЖДЕНИЯ</b>\n"
            for warning in risk_warnings[:2]:  # Максимум 2 предупреждения
                message += f"  • {warning}\n"
            message += "\n"
        
        # Итоговое заключение
        message += f"📝 <b>ЗАКЛЮЧЕНИЕ</b>\n"
        message += f"<i>{summary}</i>\n\n"
        
        # Дополнительные индикаторы
        indicators = signal_data.get('indicators', {})
        if indicators:
            message += f"📊 <b>ИНДИКАТОРЫ</b>\n"
            indicator_count = 0
            for name, value in indicators.items():
                if indicator_count >= 4:  # Максимум 4 индикатора
                    break
                if isinstance(value, (int, float)):
                    message += f"{name.upper()}: <code>{value:.2f}</code> "
                    indicator_count += 1
            message += "\n\n"
        
        # Подпись
        message += f"🔗 <i>Powered by AI Trading Bot</i>"
        
        # Обрезаем если слишком длинное
        if len(message) > self.max_message_length:
            message = message[:self.max_message_length - 50] + "\n\n<i>... сообщение обрезано</i>"
        
        return message
    
    def format_market_analysis(self, market_report: Dict[str, Any]) -> str:
        """
        Форматирует сообщение с анализом рынка
        """
        analysis = market_report.get('overall_analysis', {})
        price = market_report.get('price', 0)
        change_24h = market_report.get('change_24h', 0)
        
        # Эмодзи для фазы рынка
        phase_emoji = {
            'BULL_TREND': '🚀',
            'BEAR_TREND': '🐻', 
            'SIDEWAYS': '➡️',
            'VOLATILE': '⚡',
            'BULLISH': '📈',
            'BEARISH': '📉',
            'NEUTRAL': '😐',
            'UNKNOWN': '❓'
        }
        
        # Эмодзи для риска
        risk_emoji = {
            'LOW': '🟢',
            'MEDIUM': '🟡', 
            'HIGH': '🔴'
        }.get(analysis.get('risk_level', 'UNKNOWN'), '⚪')
        
        # Эмодзи для изменения цены
        change_emoji = '📈' if change_24h > 0 else '📉' if change_24h < 0 else '➡️'
        
        message = f"📊 <b>АНАЛИЗ РЫНКА BTC</b>\n\n"
        
        # Основные данные
        message += f"💰 Цена: <b>${price:,.2f}</b>\n"
        message += f"{change_emoji} 24ч: <b>{change_24h:+.2f}%</b>\n"
        
        # Фаза рынка
        market_phase = analysis.get('market_phase', 'UNKNOWN')
        phase_icon = phase_emoji.get(market_phase, '❓')
        message += f"📈 Фаза: <b>{market_phase}</b> {phase_icon}\n"
        
        # Уверенность и риск
        confidence = analysis.get('confidence', 0)
        message += f"🎯 Уверенность: <b>{confidence}%</b>\n"
        message += f"{risk_emoji} Риск: <b>{analysis.get('risk_level', 'UNKNOWN')}</b>\n\n"
        
        # Анализ по стратегиям
        strategy_analyses = market_report.get('strategy_analyses', [])
        if strategy_analyses:
            message += f"🔍 <b>АНАЛИЗ ПО СТРАТЕГИЯМ</b>\n"
            
            for strategy in strategy_analyses:
                signal = strategy.get('signal', 'UNKNOWN')
                confidence_str = strategy.get('confidence', 0)
                
                # Эмодзи для сигнала стратегии
                if 'STRONG_BUY' in signal:
                    signal_emoji = '🟢🟢'
                elif 'BUY' in signal:
                    signal_emoji = '🟢'
                elif 'STRONG_SELL' in signal:
                    signal_emoji = '🔴🔴'
                elif 'SELL' in signal:
                    signal_emoji = '🔴'
                else:
                    signal_emoji = '⚪'
                
                message += f"{signal_emoji} <b>{strategy.get('strategy', 'Unknown')}</b> "
                message += f"({strategy.get('timeframe', '?')}): "
                message += f"{signal} ({confidence_str}%)\n"
            
            message += "\n"
        
        # Ключевые выводы
        key_insights = analysis.get('key_insights', [])
        if key_insights:
            message += f"💡 <b>КЛЮЧЕВЫЕ ВЫВОДЫ</b>\n"
            for insight in key_insights[:3]:  # Максимум 3
                message += f"• {insight}\n"
            message += "\n"
        
        # Рекомендации
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            message += f"📋 <b>РЕКОМЕНДАЦИИ ИИ</b>\n"
            for rec in recommendations[:3]:  # Максимум 3
                message += f"• {rec}\n"
            message += "\n"
        
        # Итоговое заключение
        summary = analysis.get('summary', 'Анализ недоступен')
        if summary:
            message += f"📝 <b>ЗАКЛЮЧЕНИЕ</b>\n"
            message += f"<i>{summary}</i>\n\n"
        
        # Время анализа
        timestamp = market_report.get('timestamp', datetime.now().isoformat())
        try:
            if isinstance(timestamp, str) and timestamp.isdigit():
                time_str = datetime.fromtimestamp(int(timestamp) / 1000).strftime('%H:%M:%S')
            else:
                time_str = datetime.now().strftime('%H:%M:%S')
        except:
            time_str = datetime.now().strftime('%H:%M:%S')
        
        message += f"⏰ Анализ на: {time_str}"
        message += f"\n🔗 <i>Powered by AI Trading Bot</i>"
        
        # Обрезаем если слишком длинное
        if len(message) > self.max_message_length:
            message = message[:self.max_message_length - 100] + "\n\n<i>... отчет обрезан</i>"
        
        return message
    
    def format_trade_update(self, trade_data: Dict[str, Any]) -> str:
        """
        Форматирует обновление о сделке
        """
        status = trade_data.get('status', 'UNKNOWN')
        symbol = trade_data.get('symbol', 'Unknown')
        pnl = trade_data.get('pnl', 0)
        strategy = trade_data.get('strategy', 'Unknown')
        
        status_emoji = {
            'OPENED': '🎯',
            'CLOSED': '🏁',
            'STOPPED': '🛑',
            'PROFIT': '✅',
            'LOSS': '❌'
        }.get(status, '📊')
        
        message = f"{status_emoji} <b>ОБНОВЛЕНИЕ СДЕЛКИ</b>\n\n"
        message += f"📈 {symbol}\n"
        message += f"🎯 Стратегия: <code>{strategy}</code>\n"
        message += f"📊 Статус: <b>{status}</b>\n"
        
        if pnl != 0:
            pnl_emoji = '💰' if pnl > 0 else '💸'
            message += f"{pnl_emoji} P&L: <b>${pnl:.2f}</b>\n"
        
        # Дополнительные данные
        entry_price = trade_data.get('entry_price')
        exit_price = trade_data.get('exit_price')
        
        if entry_price:
            message += f"📍 Вход: <code>${entry_price:.2f}</code>\n"
        if exit_price:
            message += f"🚪 Выход: <code>${exit_price:.2f}</code>\n"
        
        duration = trade_data.get('duration')
        if duration:
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            if hours > 0:
                message += f"⏱ Длительность: {hours}ч {minutes}м\n"
            else:
                message += f"⏱ Длительность: {minutes}м\n"
        
        message += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        
        return message
    
    def format_daily_summary(self, summary_data: Dict[str, Any]) -> str:
        """
        Форматирует дневную сводку
        """
        date = summary_data.get('date', datetime.now().strftime('%Y-%m-%d'))
        total_trades = summary_data.get('total_trades', 0)
        profitable_trades = summary_data.get('profitable_trades', 0)
        total_pnl = summary_data.get('total_pnl', 0)
        strategies = summary_data.get('strategies', {})
        
        win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
        
        message = f"📊 <b>ДНЕВНАЯ СВОДКА</b>\n\n"
        message += f"📅 Дата: <b>{date}</b>\n"
        message += f"🎯 Сделок: <b>{total_trades}</b>\n"
        message += f"✅ Прибыльных: <b>{profitable_trades}</b>\n"
        message += f"📈 Винрейт: <b>{win_rate:.1f}%</b>\n"
        
        pnl_emoji = '💰' if total_pnl >= 0 else '💸'
        message += f"{pnl_emoji} Общий P&L: <b>${total_pnl:.2f}</b>\n"
        
        # Статистика по стратегиям
        if strategies:
            message += f"\n📈 <b>ПО СТРАТЕГИЯМ</b>\n"
            for strategy_name, stats in strategies.items():
                strategy_pnl = stats.get('pnl', 0)
                strategy_trades = stats.get('trades', 0)
                strategy_emoji = '🟢' if strategy_pnl > 0 else '🔴' if strategy_pnl < 0 else '⚪'
                
                message += f"{strategy_emoji} <b>{strategy_name}</b>: "
                message += f"{strategy_trades} сделок, "
                message += f"${strategy_pnl:.2f}\n"
        
        # Лучшая и худшая сделки
        best_trade = summary_data.get('best_trade')
        worst_trade = summary_data.get('worst_trade')
        
        if best_trade or worst_trade:
            message += f"\n🏆 <b>ЭКСТРЕМЫ</b>\n"
            
            if best_trade:
                message += f"✅ Лучшая: <b>+${best_trade:.2f}</b>\n"
            
            if worst_trade:
                message += f"❌ Худшая: <b>${worst_trade:.2f}</b>\n"
        
        return message
    
    def format_error_alert(self, error_data: Dict[str, Any]) -> str:
        """
        Форматирует уведомление об ошибке
        """
        error_type = error_data.get('type', 'UNKNOWN')
        error_message = error_data.get('message', 'Unknown error')
        timestamp = error_data.get('timestamp', datetime.now().isoformat())
        strategy = error_data.get('strategy', 'System')
        severity = error_data.get('severity', 'ERROR')
        
        # Эмодзи для серьезности
        severity_emoji = {
            'CRITICAL': '🚨',
            'ERROR': '❌',
            'WARNING': '⚠️',
            'INFO': 'ℹ️'
        }.get(severity, '❓')
        
        message = f"{severity_emoji} <b>СИСТЕМНОЕ УВЕДОМЛЕНИЕ</b>\n\n"
        message += f"🔧 Компонент: <code>{strategy}</code>\n"
        message += f"📋 Тип: <code>{error_type}</code>\n"
        message += f"🔍 Серьезность: <b>{severity}</b>\n"
        message += f"📝 Описание:\n<i>{error_message}</i>\n\n"
        
        # Время в читаемом формате
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                time_str = str(timestamp)
        except:
            time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        message += f"⏰ Время: {time_str}\n"
        
        # Рекомендации по действиям
        if severity in ['CRITICAL', 'ERROR']:
            message += f"\n🔧 <b>ТРЕБУЕТСЯ ВНИМАНИЕ</b>\n"
            message += f"• Проверьте логи системы\n"
            message += f"• Убедитесь в стабильности соединения\n"
            if error_type == 'API_ERROR':
                message += f"• Проверьте API ключи\n"
        
        return message
    
    def format_system_status(self, status_data: Dict[str, Any]) -> str:
        """
        Форматирует статус системы
        """
        strategies_status = status_data.get('strategies', {})
        ai_status = status_data.get('ai_enabled', False)
        api_status = status_data.get('api_connected', False)
        uptime = status_data.get('uptime', 0)
        
        message = f"🤖 <b>СТАТУС СИСТЕМЫ</b>\n\n"
        
        # Общий статус
        api_emoji = '✅' if api_status else '❌'
        ai_emoji = '✅' if ai_status else '❌'
        
        message += f"{api_emoji} Подключение к API: {'Активно' if api_status else 'Отключено'}\n"
        message += f"{ai_emoji} ИИ анализ: {'Включен' if ai_status else 'Отключен'}\n"
        
        # Время работы
        if uptime > 0:
            hours = uptime // 3600
            minutes = (uptime % 3600) // 60
            message += f"⏰ Время работы: {hours}ч {minutes}м\n"
        
        # Статус стратегий
        if strategies_status:
            message += f"\n📊 <b>СТРАТЕГИИ</b>\n"
            for strategy, info in strategies_status.items():
                status = info.get('status', 'unknown')
                trades_today = info.get('trades_today', 0)
                
                status_emoji = '🟢' if status == 'active' else '🟡' if status == 'paused' else '🔴'
                message += f"{status_emoji} <b>{strategy}</b>: {trades_today} сделок\n"
        
        message += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        
        return message
