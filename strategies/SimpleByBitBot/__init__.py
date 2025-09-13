# strategies/SimpleByBitBot/__init__.py
from jesse.strategies import Strategy
import jesse.indicators as ta


class SimpleByBitBot(Strategy):
    """
    Простая стратегия для тестирования с отладкой
    """
    
    def __init__(self):
        super().__init__()
        # Логируем информацию о подключении при инициализации
        self.log(f"=== SimpleByBitBot Initialized ===")
        self.log(f"Exchange: {self.exchange}")
        self.log(f"Symbol: {self.symbol}")
        self.log(f"Timeframe: {self.timeframe}")
    
    def should_long(self) -> bool:
        # Добавляем отладку для каждого вызова
        self.log(f"should_long called - index: {self.index}")
        # Простое условие: покупаем каждые 10 свечей для тестирования
        condition = self.index % 10 == 0
        if condition:
            self.log(f"LONG condition TRUE at index {self.index}")
        return condition
    
    def should_short(self) -> bool:
        return False  # Отключаем шорты для простоты
    
    def should_cancel_entry(self) -> bool:
        return False
    
    def go_long(self):
        """Открытие длинной позиции"""
        self.log(f"=== GO_LONG CALLED ===")
        self.log(f"Current price: {self.current_candle[4]}")
        self.log(f"Available balance: {self.available_margin}")
        
        qty = 0.01  # Минимальный размер для тестирования
        self.log(f"Attempting to buy {qty} at market price")
        
        try:
            self.buy = qty, self.current_candle[4]  # Market order по цене закрытия
            self.log(f"Buy order submitted successfully")
        except Exception as e:
            self.log(f"ERROR in go_long: {str(e)}")
    
    def go_short(self):
        pass
    
    def update_position(self):
        # Логируем информацию о позиции если она есть
        if self.position.is_open:
            self.log(f"Position open - qty: {self.position.qty}, pnl: {self.position.pnl}")
    
    def before(self):
        """Вызывается перед каждой свечой"""
        if self.index % 100 == 0:  # Логируем каждую 100-ю свечу
            self.log(f"Processing candle {self.index}, price: {self.current_candle[4]}")
