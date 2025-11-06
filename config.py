"""Configuration loader for environment variables."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for trading bot."""
    
    # Bybit API Configuration
    BYBIT_API_KEY = os.getenv('BYBIT_API_KEY', '')
    BYBIT_API_SECRET = os.getenv('BYBIT_API_SECRET', '')
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Trading Configuration
    LEVERAGE = int(os.getenv('LEVERAGE', '5'))  # 5x leverage (matches backtest)
    TRADING_PAIR = os.getenv('TRADING_PAIR', 'BTCUSDT')
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'demo').lower()
    INTERVAL = int(os.getenv('INTERVAL', '15'))  # 15 minutes (matches backtest)
    
    # Position Sizing (matches backtest)
    POSITION_SIZE_PCT = 0.20  # 20% of balance per position (max 5 positions = 100% exposure)
    COMMISSION_RATE = 0.00055  # Bybit futures commission (~0.055%)
    
    # SessionAware Strategy Parameters
    STRATEGY_EMA_FAST = int(os.getenv('STRATEGY_EMA_FAST', '8'))
    STRATEGY_EMA_MEDIUM = int(os.getenv('STRATEGY_EMA_MEDIUM', '21'))
    STRATEGY_EMA_SLOW = int(os.getenv('STRATEGY_EMA_SLOW', '50'))
    STRATEGY_SIGNAL_THRESHOLD = float(os.getenv('STRATEGY_SIGNAL_THRESHOLD', '0.70'))
    
    # Bybit API endpoints
    BYBIT_DEMO_API_URL = 'https://api-demo.bybit.com'
    BYBIT_REAL_API_URL = 'https://api.bybit.com'
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present."""
        errors = []
        
        if not cls.BYBIT_API_KEY:
            errors.append('BYBIT_API_KEY is required')
        if not cls.BYBIT_API_SECRET:
            errors.append('BYBIT_API_SECRET is required')
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append('TELEGRAM_BOT_TOKEN is required')
        if not cls.TELEGRAM_CHAT_ID:
            errors.append('TELEGRAM_CHAT_ID is required')
        
        if errors:
            raise ValueError(f"Missing required configuration: {', '.join(errors)}")
        
        return True
    
    @classmethod
    def get_trading_api_url(cls):
        """Get trading API URL based on environment."""
        if cls.ENVIRONMENT == 'demo':
            return cls.BYBIT_DEMO_API_URL
        return cls.BYBIT_REAL_API_URL
    
    @classmethod
    def get_market_api_url(cls):
        """Get market data API URL (always real, not testnet)."""
        return cls.BYBIT_REAL_API_URL

