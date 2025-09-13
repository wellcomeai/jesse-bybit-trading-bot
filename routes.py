routes = [
    {
        'exchange': 'Bybit USDT Perpetual',
        'symbol': 'BTCUSDT', 
        'timeframe': '5m',      # Скальпинг - быстрый таймфрейм
        'strategy': 'ActiveScalper'
    },
    {
        'exchange': 'Bybit USDT Perpetual', 
        'symbol': 'BTCUSDT',
        'timeframe': '15m',     # Баланс - средний таймфрейм  
        'strategy': 'BalancedTrader'
    },
    {
        'exchange': 'Bybit USDT Perpetual',
        'symbol': 'BTCUSDT',
        'timeframe': '1h',      # Качество - долгий таймфрейм
        'strategy': 'QualityTrader' 
    }
]
