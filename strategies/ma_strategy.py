"""Moving Average crossover strategy."""
import pandas as pd
import numpy as np


class MAStrategy:
    """Moving Average crossover strategy."""
    
    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        """
        Initialize MA strategy.
        
        Args:
            fast_period: Fast MA period (default: 20)
            slow_period: Slow MA period (default: 50)
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def calculate_ma(self, df: pd.DataFrame, period: int, column: str = 'close'):
        """Calculate Moving Average."""
        return df[column].rolling(window=period).mean()
    
    def add_indicators(self, df: pd.DataFrame):
        """Add MA indicators to dataframe."""
        df = df.copy()
        df['ma_fast'] = self.calculate_ma(df, self.fast_period)
        df['ma_slow'] = self.calculate_ma(df, self.slow_period)
        return df
    
    def get_signal(self, df: pd.DataFrame):
        """
        Get trading signal based on MA crossover.
        
        Returns:
            'BUY': Fast MA crosses above Slow MA (bullish crossover)
            'SELL': Fast MA crosses below Slow MA (bearish crossover)
            'HOLD': No signal
        """
        if len(df) < self.slow_period:
            return 'HOLD', None
        
        df = self.add_indicators(df)
        
        # Get last few candles for crossover detection
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Check if we have valid MA values
        if pd.isna(current['ma_fast']) or pd.isna(current['ma_slow']):
            return 'HOLD', None
        
        # Previous state
        prev_fast_above_slow = previous['ma_fast'] > previous['ma_slow']
        # Current state
        curr_fast_above_slow = current['ma_fast'] > current['ma_slow']
        
        # Calculate distance between MAs for confirmation
        ma_distance = abs(current['ma_fast'] - current['ma_slow']) / current['ma_slow'] * 100
        
        # Bullish crossover: Fast MA crosses above Slow MA
        if not prev_fast_above_slow and curr_fast_above_slow:
            return 'BUY', {
                'entry_price': current['close'],
                'ma_fast': current['ma_fast'],
                'ma_slow': current['ma_slow'],
                'timestamp': current['timestamp'],
                'ma_distance': ma_distance
            }
        
        # Bearish crossover: Fast MA crosses below Slow MA
        if prev_fast_above_slow and not curr_fast_above_slow:
            return 'SELL', {
                'entry_price': current['close'],
                'ma_fast': current['ma_fast'],
                'ma_slow': current['ma_slow'],
                'timestamp': current['timestamp'],
                'ma_distance': ma_distance
            }
        
        # Alternative: If no recent crossover but strong trend (for testing)
        # This helps trigger signals more frequently
        if curr_fast_above_slow and ma_distance > 0.5:  # Fast MA is significantly above Slow MA
            # Check if price is also above both MAs (strong bullish)
            if current['close'] > current['ma_fast'] and current['close'] > current['ma_slow']:
                # Check if fast MA is rising
                if len(df) >= 3:
                    prev2_fast = df.iloc[-3]['ma_fast']
                    if current['ma_fast'] > prev2_fast:  # Fast MA is rising
                        return 'BUY', {
                            'entry_price': current['close'],
                            'ma_fast': current['ma_fast'],
                            'ma_slow': current['ma_slow'],
                            'timestamp': current['timestamp'],
                            'ma_distance': ma_distance,
                            'signal_type': 'trend_follow'
                        }
        
        if not curr_fast_above_slow and ma_distance > 0.5:  # Fast MA is significantly below Slow MA
            # Check if price is also below both MAs (strong bearish)
            if current['close'] < current['ma_fast'] and current['close'] < current['ma_slow']:
                # Check if fast MA is falling
                if len(df) >= 3:
                    prev2_fast = df.iloc[-3]['ma_fast']
                    if current['ma_fast'] < prev2_fast:  # Fast MA is falling
                        return 'SELL', {
                            'entry_price': current['close'],
                            'ma_fast': current['ma_fast'],
                            'ma_slow': current['ma_slow'],
                            'timestamp': current['timestamp'],
                            'ma_distance': ma_distance,
                            'signal_type': 'trend_follow'
                        }
        
        return 'HOLD', None
    
    def calculate_tp_sl(self, entry_price: float, side: str, tp_percent: float = 1.0, sl_percent: float = 1.0):
        """
        Calculate Take Profit and Stop Loss levels.
        
        Args:
            entry_price: Entry price
            side: 'Buy' or 'Sell'
            tp_percent: Take profit percentage (default: 1.0%)
            sl_percent: Stop loss percentage (default: 1.0%)
        
        Returns:
            Dictionary with tp_price and sl_price
        """
        if side.upper() == 'BUY':
            tp_price = entry_price * (1 + tp_percent / 100)
            sl_price = entry_price * (1 - sl_percent / 100)
        else:  # SELL
            tp_price = entry_price * (1 - tp_percent / 100)
            sl_price = entry_price * (1 + sl_percent / 100)
        
        return {
            'tp_price': round(tp_price, 8),
            'sl_price': round(sl_price, 8),
            'tp_percent': tp_percent,
            'sl_percent': sl_percent
        }

