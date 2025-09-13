# enhanced_test_api.py
import os
import requests
import time
import hmac
import hashlib

def test_bybit_symbols():
    """Проверяем доступные символы на Bybit testnet"""
    print("🔍 Проверяем доступные символы на Bybit testnet...")
    
    try:
        # Публичный запрос (без API ключей)
        response = requests.get(
            'https://api-testnet.bybit.com/v5/market/instruments-info?category=linear&limit=10',
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['retCode'] == 0:
                symbols = [item['symbol'] for item in data['result']['list']]
                print(f"✅ Найдено символов: {len(symbols)}")
                print(f"📝 Первые 10 символов: {symbols}")
                
                if 'BTCUSDT' in symbols:
                    print("✅ BTCUSDT доступен на Bybit testnet!")
                else:
                    print("❌ BTCUSDT НЕ найден в списке")
            else:
                print(f"❌ Ошибка API: {data['retMsg']}")
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")

def test_api_authentication():
    """Проверяем аутентификацию API ключей"""
    api_key = os.getenv('BYBIT_USDT_PERPETUAL_TESTNET_API_KEY')
    api_secret = os.getenv('BYBIT_USDT_PERPETUAL_TESTNET_API_SECRET')
    
    print(f"\n🔑 Проверяем API ключи...")
    print(f"API Key длина: {len(api_key) if api_key else 0} символов")
    print(f"API Secret длина: {len(api_secret) if api_secret else 0} символов")
    
    if not api_key or not api_secret:
        print("❌ API ключи не найдены в переменных окружения!")
        return False
        
    if len(api_key) < 20:
        print("⚠️ API ключ подозрительно короткий (должен быть 20+ символов)")
        
    # Тестируем аутентифицированный запрос
    try:
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        
        param_str = f"{timestamp}{api_key}{recv_window}"
        signature = hmac.new(
            api_secret.encode('utf-8'),
            param_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'X-BAPI-API-KEY': api_key,
            'X-BAPI-TIMESTAMP': timestamp,
            'X-BAPI-RECV-WINDOW': recv_window,
            'X-BAPI-SIGN': signature
        }
        
        response = requests.get(
            'https://api-testnet.bybit.com/v5/account/wallet-balance?accountType=UNIFIED',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['retCode'] == 0:
                print("✅ API ключи работают! Аутентификация успешна")
                print(f"📊 Данные аккаунта получены: {data['result']}")
                return True
            else:
                print(f"❌ Ошибка API: {data['retMsg']} (код: {data['retCode']})")
                return False
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            print(f"Ответ: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка аутентификации: {e}")
        return False

if __name__ == "__main__":
    test_bybit_symbols()
    test_api_authentication()
