routes = [
    # === ТЕСТОВАЯ СТРАТЕГИЯ ДЛЯ ПРОВЕРКИ СИГНАЛОВ ===
    {
        'exchange': 'Bybit USDT Perpetual',
        'symbol': 'BTCUSDT',
        'timeframe': '5m',           # 1 МИНУТА для частых сигналов
        'strategy': 'TestSignalStrategy'  # Новая тестовая стратегия
    },
    
    # === ОСНОВНЫЕ СТРАТЕГИИ (временно отключены для теста) ===
    # {
    #     'exchange': 'Bybit USDT Perpetual',
    #     'symbol': 'BTCUSDT', 
    #     'timeframe': '5m',      # Скальпинг - быстрый таймфрейм
    #     'strategy': 'ActiveScalper'
    # },
    # {
    #     'exchange': 'Bybit USDT Perpetual', 
    #     'symbol': 'BTCUSDT',
    #     'timeframe': '15m',     # Баланс - средний таймфрейм  
    #     'strategy': 'BalancedTrader'
    # },
    # {
    #     'exchange': 'Bybit USDT Perpetual',
    #     'symbol': 'BTCUSDT',
    #     'timeframe': '1h',      # Качество - долгий таймфрейм
    #     'strategy': 'QualityTrader' 
    # }
]
