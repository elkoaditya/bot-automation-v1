"""Chart generator for trading visualization."""
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import pandas as pd
import numpy as np
import os


class ChartGenerator:
    """Generate trading charts with indicators and positions."""
    
    def __init__(self, output_dir: str = '/tmp'):
        """Initialize chart generator."""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_entry_chart(self, df: pd.DataFrame, entry_price: float, 
                            tp_price: float, sl_price: float, 
                            ma_fast: float, ma_slow: float,
                            symbol: str, side: str, leverage: int):
        """
        Generate entry chart with candlestick, MA lines, entry, TP, SL.
        
        Args:
            df: DataFrame with OHLCV data
            entry_price: Entry price
            tp_price: Take profit price
            sl_price: Stop loss price
            ma_fast: Fast MA value
            ma_slow: Slow MA value
            symbol: Trading pair symbol
            side: 'Buy' or 'Sell'
            leverage: Leverage used
        
        Returns:
            Path to saved chart image
        """
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Use last 100 candles for better visualization
        plot_df = df.tail(100).copy()
        
        # Plot candlestick
        self._plot_candlestick(ax, plot_df)
        
        # Calculate and plot MA lines
        if 'ma_fast' not in plot_df.columns:
            plot_df['ma_fast'] = plot_df['close'].rolling(window=20).mean()
            plot_df['ma_slow'] = plot_df['close'].rolling(window=50).mean()
        
        ax.plot(plot_df['timestamp'], plot_df['ma_fast'], 
                label=f'MA Fast (20)', color='blue', linewidth=1.5, alpha=0.7)
        ax.plot(plot_df['timestamp'], plot_df['ma_slow'], 
                label=f'MA Slow (50)', color='orange', linewidth=1.5, alpha=0.7)
        
        # Plot horizontal lines for entry, TP, SL
        last_timestamp = plot_df['timestamp'].iloc[-1]
        ax.axhline(y=entry_price, color='green', linestyle='--', 
                  linewidth=2, label=f'Entry: ${entry_price:.2f}', alpha=0.8)
        ax.axhline(y=tp_price, color='blue', linestyle='--', 
                  linewidth=2, label=f'TP: ${tp_price:.2f}', alpha=0.8)
        ax.axhline(y=sl_price, color='red', linestyle='--', 
                  linewidth=2, label=f'SL: ${sl_price:.2f}', alpha=0.8)
        
        # Add entry marker
        entry_idx = len(plot_df) - 1
        marker_color = 'green' if side.upper() == 'BUY' else 'red'
        marker_shape = '^' if side.upper() == 'BUY' else 'v'
        ax.scatter([plot_df['timestamp'].iloc[entry_idx]], [entry_price], 
                  color=marker_color, marker=marker_shape, s=200, 
                  zorder=5, edgecolors='black', linewidths=2,
                  label=f'Entry ({side.upper()})')
        
        # Formatting
        ax.set_title(f'{symbol} - Entry Signal ({side.upper()}) | Leverage: {leverage}x', 
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Price (USDT)', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save chart
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{symbol}_{side.lower()}_entry_{timestamp}.png'
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_exit_chart(self, df: pd.DataFrame, entry_price: float,
                           exit_price: float, tp_price: float, sl_price: float,
                           symbol: str, side: str, pnl: float, pnl_percent: float):
        """
        Generate exit chart showing entry, exit, TP, SL.
        
        Args:
            df: DataFrame with OHLCV data
            entry_price: Entry price
            exit_price: Exit price
            tp_price: Take profit price
            sl_price: Stop loss price
            symbol: Trading pair symbol
            side: 'Buy' or 'Sell'
            pnl: Profit/Loss amount
            pnl_percent: Profit/Loss percentage
        
        Returns:
            Path to saved chart image
        """
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Use last 100 candles
        plot_df = df.tail(100).copy()
        
        # Plot candlestick
        self._plot_candlestick(ax, plot_df)
        
        # Calculate and plot MA lines
        if 'ma_fast' not in plot_df.columns:
            plot_df['ma_fast'] = plot_df['close'].rolling(window=20).mean()
            plot_df['ma_slow'] = plot_df['close'].rolling(window=50).mean()
        
        ax.plot(plot_df['timestamp'], plot_df['ma_fast'], 
                label=f'MA Fast (20)', color='blue', linewidth=1.5, alpha=0.7)
        ax.plot(plot_df['timestamp'], plot_df['ma_slow'], 
                label=f'MA Slow (50)', color='orange', linewidth=1.5, alpha=0.7)
        
        # Plot horizontal lines
        ax.axhline(y=entry_price, color='green', linestyle='--', 
                  linewidth=2, label=f'Entry: ${entry_price:.2f}', alpha=0.8)
        ax.axhline(y=exit_price, color='purple', linestyle='--', 
                  linewidth=2, label=f'Exit: ${exit_price:.2f}', alpha=0.8)
        ax.axhline(y=tp_price, color='blue', linestyle=':', 
                  linewidth=1.5, label=f'TP: ${tp_price:.2f}', alpha=0.6)
        ax.axhline(y=sl_price, color='red', linestyle=':', 
                  linewidth=1.5, label=f'SL: ${sl_price:.2f}', alpha=0.6)
        
        # Add entry and exit markers
        entry_idx = len(plot_df) - 1
        exit_idx = len(plot_df) - 1
        
        entry_color = 'green' if side.upper() == 'BUY' else 'red'
        exit_color = 'green' if pnl >= 0 else 'red'
        
        ax.scatter([plot_df['timestamp'].iloc[entry_idx]], [entry_price], 
                  color=entry_color, marker='^' if side.upper() == 'BUY' else 'v', 
                  s=200, zorder=5, edgecolors='black', linewidths=2,
                  label=f'Entry ({side.upper()})')
        ax.scatter([plot_df['timestamp'].iloc[exit_idx]], [exit_price], 
                  color=exit_color, marker='x', s=300, zorder=5, 
                  edgecolors='black', linewidths=2, label='Exit')
        
        # Formatting
        pnl_sign = '+' if pnl >= 0 else ''
        ax.set_title(f'{symbol} - Exit | PnL: {pnl_sign}${pnl:.2f} ({pnl_sign}{pnl_percent:.2f}%)', 
                    fontsize=16, fontweight='bold', pad=20, 
                    color='green' if pnl >= 0 else 'red')
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Price (USDT)', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save chart
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{symbol}_{side.lower()}_exit_{timestamp}.png'
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_analysis_chart(self, df: pd.DataFrame, symbol: str, 
                               current_price: float, ema_fast: float, 
                               ema_medium: float, ema_slow: float,
                               rsi: float, bb_upper: float, bb_middle: float, 
                               bb_lower: float, long_strength: float, 
                               short_strength: float, session: str):
        """
        Generate analysis chart with all strategy indicators.
        
        Args:
            df: DataFrame with OHLCV and indicators
            symbol: Trading pair symbol
            current_price: Current price
            ema_fast: Fast EMA value
            ema_medium: Medium EMA value
            ema_slow: Slow EMA value
            rsi: RSI value
            bb_upper: Bollinger Band upper
            bb_middle: Bollinger Band middle
            bb_lower: Bollinger Band lower
            long_strength: Long signal strength
            short_strength: Short signal strength
            session: Current session name
        
        Returns:
            Path to saved chart image
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                       gridspec_kw={'height_ratios': [3, 1]})
        
        # Use last 100 candles
        plot_df = df.tail(100).copy()
        
        # Plot candlestick on main chart
        self._plot_candlestick(ax1, plot_df)
        
        # Plot EMA lines
        if 'ema_fast' in plot_df.columns:
            ax1.plot(plot_df['timestamp'], plot_df['ema_fast'], 
                    label='EMA Fast (8)', color='blue', linewidth=1.5, alpha=0.8)
        if 'ema_medium' in plot_df.columns:
            ax1.plot(plot_df['timestamp'], plot_df['ema_medium'], 
                    label='EMA Medium (21)', color='orange', linewidth=1.5, alpha=0.8)
        if 'ema_slow' in plot_df.columns:
            ax1.plot(plot_df['timestamp'], plot_df['ema_slow'], 
                    label='EMA Slow (50)', color='red', linewidth=1.5, alpha=0.8)
        
        # Plot Bollinger Bands
        if 'bb_upper' in plot_df.columns:
            ax1.plot(plot_df['timestamp'], plot_df['bb_upper'], 
                    label='BB Upper', color='gray', linestyle='--', linewidth=1, alpha=0.6)
            ax1.plot(plot_df['timestamp'], plot_df['bb_middle'], 
                    label='BB Middle', color='gray', linestyle='-', linewidth=1, alpha=0.4)
            ax1.plot(plot_df['timestamp'], plot_df['bb_lower'], 
                    label='BB Lower', color='gray', linestyle='--', linewidth=1, alpha=0.6)
            ax1.fill_between(plot_df['timestamp'], plot_df['bb_upper'], plot_df['bb_lower'], 
                           alpha=0.1, color='gray')
        
        # Plot current price line
        last_timestamp = plot_df['timestamp'].iloc[-1]
        ax1.axhline(y=current_price, color='purple', linestyle='-', 
                   linewidth=2, label=f'Current: ${current_price:.2f}', alpha=0.8)
        
        # Format main chart
        max_strength = max(long_strength, short_strength)
        signal_text = ""
        if long_strength > 0.70:
            signal_text = f"LONG {int(long_strength*100)}%"
        elif short_strength > 0.70:
            signal_text = f"SHORT {int(short_strength*100)}%"
        else:
            signal_text = f"CONF {int(max_strength*100)}%"
        
        ax1.set_title(f'{symbol} - Analysis | {session.upper()} Session | Signal: {signal_text}', 
                     fontsize=16, fontweight='bold', pad=20)
        ax1.set_ylabel('Price (USDT)', fontsize=12)
        ax1.legend(loc='best', fontsize=9, ncol=2)
        ax1.grid(True, alpha=0.3)
        
        # Plot RSI on subplot
        if 'rsi' in plot_df.columns:
            ax2.plot(plot_df['timestamp'], plot_df['rsi'], 
                    label='RSI', color='purple', linewidth=1.5)
            ax2.axhline(y=70, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Overbought')
            ax2.axhline(y=30, color='green', linestyle='--', linewidth=1, alpha=0.5, label='Oversold')
            ax2.axhline(y=50, color='gray', linestyle=':', linewidth=0.5, alpha=0.3)
            ax2.fill_between(plot_df['timestamp'], 70, 100, alpha=0.1, color='red')
            ax2.fill_between(plot_df['timestamp'], 0, 30, alpha=0.1, color='green')
        
        ax2.set_ylabel('RSI', fontsize=12)
        ax2.set_xlabel('Time', fontsize=12)
        ax2.set_ylim(0, 100)
        ax2.legend(loc='best', fontsize=9)
        ax2.grid(True, alpha=0.3)
        
        # Format x-axis dates
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # Save chart
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{symbol}_analysis_{timestamp}.png'
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def _plot_candlestick(self, ax, df: pd.DataFrame):
        """Plot candlestick chart."""
        for idx, row in df.iterrows():
            timestamp = row['timestamp']
            open_price = row['open']
            high_price = row['high']
            low_price = row['low']
            close_price = row['close']
            
            color = 'green' if close_price >= open_price else 'red'
            
            # Draw the high-low line
            ax.plot([timestamp, timestamp], [low_price, high_price], 
                   color='black', linewidth=0.5)
            
            # Draw the open-close box
            body_height = abs(close_price - open_price)
            body_bottom = min(open_price, close_price)
            
            ax.bar(timestamp, body_height, bottom=body_bottom, 
                  width=0.0008, color=color, alpha=0.8, edgecolor='black', linewidth=0.5)

