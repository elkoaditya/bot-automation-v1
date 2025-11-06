"""
Session-Aware Multi-Strategy Trading System for Live Trading

Strategy ini menggunakan logic berbeda berdasarkan waktu market aktif:
- Asian Session (00:00-09:00 UTC): Mean reversion, ranging market
- European Session (09:00-17:00 UTC): Trend following dengan filter ketat
- US Session (17:00-00:00 UTC): Aggressive trend following, high volatility

Setiap session memiliki karakteristik volatility dan behavior yang berbeda.
Strategy menyesuaikan parameter secara dinamis berdasarkan session aktif.
"""
import pandas as pd
import numpy as np
import ta
from datetime import datetime
from typing import Tuple, Dict, Optional


class SessionAwareStrategy:
    """
    Session-Aware Strategy yang adaptif terhadap kondisi market berbeda
    di setiap trading session (Asian, European, US)
    """
    
    def __init__(self, 
                 ema_fast: int = 8,
                 ema_medium: int = 21,
                 ema_slow: int = 50,
                 rsi_period: int = 14,
                 bb_period: int = 20,
                 bb_std: float = 2.0,
                 macd_fast: int = 12,
                 macd_slow: int = 26,
                 macd_signal: int = 9,
                 atr_period: int = 14,
                 volume_ma_period: int = 20,
                 trend_strength_threshold: float = 0.002,
                 signal_threshold: float = 0.70):
        """
        Initialize Session-Aware Strategy
        
        Args:
            ema_fast: Fast EMA period (default: 8)
            ema_medium: Medium EMA period (default: 21)
            ema_slow: Slow EMA period (default: 50)
            rsi_period: RSI period (default: 14)
            bb_period: Bollinger Bands period (default: 20)
            bb_std: Bollinger Bands standard deviation (default: 2.0)
            macd_fast: MACD fast period (default: 12)
            macd_slow: MACD slow period (default: 26)
            macd_signal: MACD signal period (default: 9)
            atr_period: ATR period (default: 14)
            volume_ma_period: Volume MA period (default: 20)
            trend_strength_threshold: Minimum trend strength (default: 0.002)
            signal_threshold: Minimum signal confidence (default: 0.70)
        """
        self.ema_fast = ema_fast
        self.ema_medium = ema_medium
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.atr_period = atr_period
        self.volume_ma_period = volume_ma_period
        self.trend_strength_threshold = trend_strength_threshold
        self.signal_threshold = signal_threshold
        
        # Session-specific RSI thresholds
        self.rsi_asian = {'overbought': 60, 'oversold': 40}
        self.rsi_european = {'overbought': 65, 'oversold': 35}
        self.rsi_us = {'overbought': 70, 'oversold': 30}
        
        # Session-specific ATR multipliers
        self.atr_asian = 1.0
        self.atr_european = 1.5
        self.atr_us = 2.0
        
        # Session-specific volume multipliers
        self.vol_asian = 0.8
        self.vol_european = 1.0
        self.vol_us = 1.2
    
    def get_session(self, timestamp: pd.Timestamp = None) -> str:
        """
        Determine market session based on UTC time
        
        Args:
            timestamp: Timestamp to check (default: now)
        
        Returns:
            'asian', 'european', or 'us'
        """
        if timestamp is None:
            # Use now() with UTC timezone instead of deprecated utcnow()
            timestamp = pd.Timestamp.now(tz='UTC')
        
        # Convert to UTC if not already
        if timestamp.tz is not None:
            timestamp = timestamp.tz_convert('UTC')
        else:
            # Timestamp tanpa timezone dianggap UTC (Bybit mengembalikan UTC)
            # Localize ke UTC untuk memastikan konsistensi
            timestamp = timestamp.tz_localize('UTC')
        
        hour = timestamp.hour
        
        if 0 <= hour < 9:
            return 'asian'
        elif 9 <= hour < 17:
            return 'european'
        else:  # 17 <= hour < 24
            return 'us'
    
    def get_session_parameters(self, session: str) -> Dict:
        """
        Get dynamic parameters based on current session
        
        Args:
            session: 'asian', 'european', or 'us'
        
        Returns:
            Dictionary with session-specific parameters
        """
        if session == 'asian':
            return {
                'rsi_overbought': self.rsi_asian['overbought'],
                'rsi_oversold': self.rsi_asian['oversold'],
                'atr_multiplier': self.atr_asian,
                'min_volume_mult': self.vol_asian,
                'trend_bias': 0.4,  # 40% trend
                'mean_reversion_bias': 0.6,  # 60% mean reversion
            }
        elif session == 'european':
            return {
                'rsi_overbought': self.rsi_european['overbought'],
                'rsi_oversold': self.rsi_european['oversold'],
                'atr_multiplier': self.atr_european,
                'min_volume_mult': self.vol_european,
                'trend_bias': 0.7,  # 70% trend
                'mean_reversion_bias': 0.3,  # 30% mean reversion
            }
        else:  # US session
            return {
                'rsi_overbought': self.rsi_us['overbought'],
                'rsi_oversold': self.rsi_us['oversold'],
                'atr_multiplier': self.atr_us,
                'min_volume_mult': self.vol_us,
                'trend_bias': 0.85,  # 85% trend
                'mean_reversion_bias': 0.15,  # 15% mean reversion
            }
    
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add all technical indicators to dataframe
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            DataFrame with added indicators
        """
        df = df.copy()
        
        # EMAs
        df['ema_fast'] = ta.trend.EMAIndicator(df['close'], window=self.ema_fast).ema_indicator()
        df['ema_medium'] = ta.trend.EMAIndicator(df['close'], window=self.ema_medium).ema_indicator()
        df['ema_slow'] = ta.trend.EMAIndicator(df['close'], window=self.ema_slow).ema_indicator()
        
        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=self.rsi_period).rsi()
        
        # Bollinger Bands
        bb_indicator = ta.volatility.BollingerBands(df['close'], window=self.bb_period, window_dev=self.bb_std)
        df['bb_upper'] = bb_indicator.bollinger_hband()
        df['bb_middle'] = bb_indicator.bollinger_mavg()
        df['bb_lower'] = bb_indicator.bollinger_lband()
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # MACD
        macd_indicator = ta.trend.MACD(
            df['close'],
            window_fast=self.macd_fast,
            window_slow=self.macd_slow,
            window_sign=self.macd_signal
        )
        df['macd'] = macd_indicator.macd()
        df['macd_signal'] = macd_indicator.macd_signal()
        df['macd_diff'] = macd_indicator.macd_diff()
        
        # ATR
        df['atr'] = ta.volatility.AverageTrueRange(
            df['high'], df['low'], df['close'], 
            window=self.atr_period
        ).average_true_range()
        df['atr_pct'] = df['atr'] / df['close']
        
        # Volume
        df['volume_ma'] = df['volume'].rolling(window=self.volume_ma_period).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        return df
    
    def calculate_signal_strength(self, df: pd.DataFrame, session_params: Dict) -> Tuple[float, float]:
        """
        Calculate long and short signal strength
        
        Args:
            df: DataFrame with indicators
            session_params: Session-specific parameters
        
        Returns:
            Tuple of (long_signal_strength, short_signal_strength)
        """
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # === LONG SIGNAL STRENGTH ===
        
        # Trend following conditions
        long_trend_alignment = float((current['ema_fast'] > current['ema_medium']) and 
                                     (current['ema_medium'] > current['ema_slow']))
        long_price_above_ema = float(current['close'] > current['ema_slow'])
        long_price_above_fast = float(current['close'] > current['ema_fast'])
        long_ema_gap = float(((current['ema_fast'] - current['ema_slow']) / current['ema_slow']) > self.trend_strength_threshold)
        long_ema_cross = float((current['ema_fast'] > current['ema_medium']) and 
                              (previous['ema_fast'] <= previous['ema_medium']))
        long_macd_bullish = float((current['macd'] > current['macd_signal']) and (current['macd_diff'] > 0))
        long_macd_cross = float((current['macd'] > current['macd_signal']) and 
                               (previous['macd'] <= previous['macd_signal']))
        
        # Trend score
        trend_score = (
            long_trend_alignment * 0.2 +
            long_price_above_ema * 0.15 +
            long_price_above_fast * 0.15 +
            long_ema_gap * 0.15 +
            long_ema_cross * 0.15 +
            long_macd_bullish * 0.1 +
            long_macd_cross * 0.1
        )
        
        # Momentum confirmation
        if len(df) >= 4:
            trend_momentum = float(current['close'] > df.iloc[-4]['close'])
            ema_momentum = float(current['ema_fast'] > df.iloc[-3]['ema_fast'])
            trend_score = trend_score * 0.75 + (trend_momentum * 0.125 + ema_momentum * 0.125)
        
        # Mean reversion conditions
        long_bb_oversold = float(current['bb_position'] < 0.25)
        long_bb_bounce = float((current['close'] > previous['close']) and 
                              (previous['close'] < df.iloc[-3]['close']))
        long_rsi_oversold = float(current['rsi'] < session_params['rsi_oversold'])
        long_below_bb = float(current['close'] < current['bb_lower'])
        
        # Mean reversion score
        mr_score = (
            long_bb_oversold * 0.25 +
            long_bb_bounce * 0.35 +
            long_rsi_oversold * 0.2 +
            long_below_bb * 0.2
        )
        
        # Volume confirmation
        volume_surge = float(current['volume_ratio'] > 1.5)
        mr_score = mr_score * 0.8 + volume_surge * 0.2
        
        # Combined long signal strength
        long_signal_strength = (
            trend_score * session_params['trend_bias'] +
            mr_score * session_params['mean_reversion_bias']
        )
        
        # === SHORT SIGNAL STRENGTH ===
        
        # Trend following conditions
        short_trend_alignment = float((current['ema_fast'] < current['ema_medium']) and 
                                      (current['ema_medium'] < current['ema_slow']))
        short_price_below_ema = float(current['close'] < current['ema_slow'])
        short_price_below_fast = float(current['close'] < current['ema_fast'])
        short_ema_gap = float(((current['ema_slow'] - current['ema_fast']) / current['ema_slow']) > self.trend_strength_threshold)
        short_ema_cross = float((current['ema_fast'] < current['ema_medium']) and 
                               (previous['ema_fast'] >= previous['ema_medium']))
        short_macd_bearish = float((current['macd'] < current['macd_signal']) and (current['macd_diff'] < 0))
        short_macd_cross = float((current['macd'] < current['macd_signal']) and 
                                (previous['macd'] >= previous['macd_signal']))
        
        # Trend score
        trend_score_short = (
            short_trend_alignment * 0.2 +
            short_price_below_ema * 0.15 +
            short_price_below_fast * 0.15 +
            short_ema_gap * 0.15 +
            short_ema_cross * 0.15 +
            short_macd_bearish * 0.1 +
            short_macd_cross * 0.1
        )
        
        # Momentum confirmation
        if len(df) >= 4:
            trend_momentum_short = float(current['close'] < df.iloc[-4]['close'])
            ema_momentum_short = float(current['ema_fast'] < df.iloc[-3]['ema_fast'])
            trend_score_short = trend_score_short * 0.75 + (trend_momentum_short * 0.125 + ema_momentum_short * 0.125)
        
        # Mean reversion conditions
        short_bb_overbought = float(current['bb_position'] > 0.75)
        short_bb_drop = float((current['close'] < previous['close']) and 
                             (previous['close'] > df.iloc[-3]['close']))
        short_rsi_overbought = float(current['rsi'] > session_params['rsi_overbought'])
        short_above_bb = float(current['close'] > current['bb_upper'])
        
        # Mean reversion score
        mr_score_short = (
            short_bb_overbought * 0.25 +
            short_bb_drop * 0.35 +
            short_rsi_overbought * 0.2 +
            short_above_bb * 0.2
        )
        
        # Volume confirmation
        mr_score_short = mr_score_short * 0.8 + volume_surge * 0.2
        
        # Combined short signal strength
        short_signal_strength = (
            trend_score_short * session_params['trend_bias'] +
            mr_score_short * session_params['mean_reversion_bias']
        )
        
        return long_signal_strength, short_signal_strength
    
    def get_signal(self, df: pd.DataFrame) -> Tuple[str, Optional[Dict]]:
        """
        Get trading signal based on current market conditions and session
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            Tuple of (signal, signal_data)
            signal: 'BUY', 'SELL', or 'HOLD'
            signal_data: Dictionary with signal details or None
        """
        if len(df) < max(self.ema_slow, self.bb_period, self.volume_ma_period):
            return 'HOLD', None
        
        # Add all indicators
        df = self.add_indicators(df)
        
        # Get current session
        current_timestamp = df.iloc[-1]['timestamp']
        session = self.get_session(current_timestamp)
        session_params = self.get_session_parameters(session)
        
        # Get current candle data
        current = df.iloc[-1]
        
        # Check for NaN values in critical indicators
        if pd.isna(current['ema_fast']) or pd.isna(current['ema_slow']) or pd.isna(current['rsi']):
            return 'HOLD', None
        
        # Calculate signal strengths
        long_strength, short_strength = self.calculate_signal_strength(df, session_params)
        
        # Volume check
        volume_ok = current['volume_ratio'] > session_params['min_volume_mult']
        
        # RSI safety filters
        long_not_overbought = current['rsi'] < session_params['rsi_overbought']
        short_not_oversold = current['rsi'] > session_params['rsi_oversold']
        
        # === BUY SIGNAL ===
        if (long_strength > self.signal_threshold and 
            volume_ok and 
            long_not_overbought):
            
            return 'BUY', {
                'entry_price': current['close'],
                'signal_strength': long_strength,
                'session': session,
                'rsi': current['rsi'],
                'ema_fast': current['ema_fast'],
                'ema_medium': current['ema_medium'],
                'ema_slow': current['ema_slow'],
                'macd': current['macd'],
                'macd_signal': current['macd_signal'],
                'bb_position': current['bb_position'],
                'volume_ratio': current['volume_ratio'],
                'atr_pct': current['atr_pct'],
                'timestamp': current['timestamp']
            }
        
        # === SELL SIGNAL ===
        if (short_strength > self.signal_threshold and 
            volume_ok and 
            short_not_oversold):
            
            return 'SELL', {
                'entry_price': current['close'],
                'signal_strength': short_strength,
                'session': session,
                'rsi': current['rsi'],
                'ema_fast': current['ema_fast'],
                'ema_medium': current['ema_medium'],
                'ema_slow': current['ema_slow'],
                'macd': current['macd'],
                'macd_signal': current['macd_signal'],
                'bb_position': current['bb_position'],
                'volume_ratio': current['volume_ratio'],
                'atr_pct': current['atr_pct'],
                'timestamp': current['timestamp']
            }
        
        return 'HOLD', None
    
    def calculate_tp_sl(self, entry_price: float, side: str, 
                       atr_pct: float = None, session: str = None,
                       tp_percent: float = None, sl_percent: float = None) -> Dict:
        """
        Calculate Take Profit and Stop Loss levels based on session and ATR
        
        Args:
            entry_price: Entry price
            side: 'Buy' or 'Sell'
            atr_pct: ATR as percentage of price (optional, will use default if not provided)
            session: Current session ('asian', 'european', 'us')
            tp_percent: Override TP percentage (optional)
            sl_percent: Override SL percentage (optional)
        
        Returns:
            Dictionary with tp_price, sl_price, tp_percent, sl_percent
        """
        # Determine session if not provided
        if session is None:
            session = self.get_session()
        
        session_params = self.get_session_parameters(session)
        atr_multiplier = session_params['atr_multiplier']
        
        # Calculate dynamic TP/SL based on ATR if provided
        if atr_pct is not None and tp_percent is None and sl_percent is None:
            # Stop loss
            sl_pct = atr_pct * atr_multiplier * 100  # Convert to percentage
            
            # Take profit (session-specific R:R ratio)
            if session == 'asian':
                tp_pct = sl_pct * 1.5  # 1:1.5 R:R
            elif session == 'european':
                tp_pct = sl_pct * 2.0  # 1:2.0 R:R
            else:  # US
                tp_pct = sl_pct * 2.5  # 1:2.5 R:R
        else:
            # Use provided percentages or defaults
            sl_pct = sl_percent if sl_percent is not None else 2.5
            tp_pct = tp_percent if tp_percent is not None else 5.0
        
        # Calculate prices
        if side.upper() == 'BUY':
            tp_price = entry_price * (1 + tp_pct / 100)
            sl_price = entry_price * (1 - sl_pct / 100)
        else:  # SELL
            tp_price = entry_price * (1 - tp_pct / 100)
            sl_price = entry_price * (1 + sl_pct / 100)
        
        return {
            'tp_price': round(tp_price, 8),
            'sl_price': round(sl_price, 8),
            'tp_percent': tp_pct,
            'sl_percent': sl_pct,
            'session': session,
            'atr_multiplier': atr_multiplier
        }

