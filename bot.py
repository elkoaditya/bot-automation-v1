#!/usr/bin/env python3
"""Main trading bot script."""
import time
import sys
from datetime import datetime
import traceback
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Force unbuffered output for Docker (redundant if using -u flag, but helps)
import os
os.environ['PYTHONUNBUFFERED'] = '1'

from config import Config
from exchanges.bybit_client import BybitClient
from strategies.ma_strategy import MAStrategy
from strategies.session_aware_strategy import SessionAwareStrategy
from notifications.telegram_bot import TelegramNotifier
from notifications.telegram_command_handler import TelegramCommandHandler
from utils.chart_generator import ChartGenerator


class TradingBot:
    """Main trading bot class."""
    
    def __init__(self):
        """Initialize trading bot."""
        print("Initializing trading bot...", flush=True)
        
        # Validate configuration
        try:
            Config.validate()
            print("✓ Configuration validated", flush=True)
        except ValueError as e:
            print(f"✗ Configuration error: {e}", flush=True)
            sys.exit(1)
        
        # Initialize components
        try:
            print("Initializing Bybit client...", flush=True)
            self.client = BybitClient()
            print("✓ Bybit client initialized", flush=True)
        except Exception as e:
            print(f"✗ Failed to initialize Bybit client: {e}", flush=True)
            traceback.print_exc()
            sys.exit(1)
        
        try:
            print("Initializing strategy...", flush=True)
            # Initialize SessionAwareStrategy with default parameters
            self.strategy = SessionAwareStrategy(
                ema_fast=Config.STRATEGY_EMA_FAST,
                ema_medium=Config.STRATEGY_EMA_MEDIUM,
                ema_slow=Config.STRATEGY_EMA_SLOW,
                signal_threshold=Config.STRATEGY_SIGNAL_THRESHOLD
            )
            print("✓ SessionAwareStrategy initialized", flush=True)
        except Exception as e:
            print(f"✗ Failed to initialize strategy: {e}", flush=True)
            traceback.print_exc()
            sys.exit(1)
        
        try:
            print("Initializing Telegram notifier...", flush=True)
            self.notifier = TelegramNotifier()
            print("✓ Telegram notifier initialized", flush=True)
        except Exception as e:
            print(f"✗ Failed to initialize Telegram notifier: {e}", flush=True)
            traceback.print_exc()
            sys.exit(1)
        
        try:
            print("Initializing chart generator...", flush=True)
            self.chart_generator = ChartGenerator()
            print("✓ Chart generator initialized", flush=True)
        except Exception as e:
            print(f"✗ Failed to initialize chart generator: {e}", flush=True)
            traceback.print_exc()
            sys.exit(1)
        
        try:
            print("Initializing Telegram command handler...", flush=True)
            self.command_handler = TelegramCommandHandler(self)
            print("✓ Telegram command handler initialized", flush=True)
        except Exception as e:
            print(f"✗ Failed to initialize Telegram command handler: {e}", flush=True)
            traceback.print_exc()
            sys.exit(1)
        
        self.leverage = Config.LEVERAGE
        self.interval = str(Config.INTERVAL)
        
        # Fixed TP/SL (matching backtest config)
        self.stop_loss_pct = 0.025   # 2.5% stop loss (matches backtest)
        self.take_profit_pct = 0.05  # 5.0% take profit (matches backtest)
        
        # Multi-coin tracking
        self.trending_coins = []
        self.positions = {}  # {symbol: position_data}
        self.positions_lock = threading.Lock()  # Thread-safe access to positions
        
        print(f"✓ Bot initialized", flush=True)
        print(f"  Leverage: {self.leverage}x", flush=True)
        print(f"  Interval: {self.interval}m", flush=True)
        print(f"  Environment: {Config.ENVIRONMENT}", flush=True)
        print(f"  Stop Loss: {self.stop_loss_pct*100}%", flush=True)
        print(f"  Take Profit: {self.take_profit_pct*100}%", flush=True)
    
    def calculate_fixed_tp_sl(self, entry_price: float, side: str):
        """
        Calculate fixed TP/SL (matching backtest config)
        
        Args:
            entry_price: Entry price
            side: 'Buy' or 'Sell'
        
        Returns:
            Dictionary with tp_price and sl_price
        """
        if side == 'Buy':
            tp_price = entry_price * (1 + self.take_profit_pct)
            sl_price = entry_price * (1 - self.stop_loss_pct)
        else:  # Sell
            tp_price = entry_price * (1 - self.take_profit_pct)
            sl_price = entry_price * (1 + self.stop_loss_pct)
        
        return {
            'tp_price': round(tp_price, 8),
            'sl_price': round(sl_price, 8),
            'tp_percent': self.take_profit_pct * 100,
            'sl_percent': self.stop_loss_pct * 100
        }
    
    def get_trending_coins(self):
        """Get top 20 trending coins."""
        try:
            print("📊 Fetching top 20 trending coins...", flush=True)
            coins = self.client.get_top_trending_coins(limit=20)
            print(f"✓ Found {len(coins)} trending coins: {', '.join(coins)}", flush=True)
            return coins
        except Exception as e:
            print(f"✗ Failed to get trending coins: {e}", flush=True)
            # Fallback to default pair
            return [Config.TRADING_PAIR]
    
    def setup_leverage_for_all_coins(self, symbols: list):
        """Setup leverage for all coins."""
        success_count = 0
        for symbol in symbols:
            try:
                self.client.set_leverage(symbol, self.leverage)
                print(f"✓ Leverage set to {self.leverage}x for {symbol}", flush=True)
                success_count += 1
            except Exception as e:
                error_msg = str(e)
                if "leverage not modified" in error_msg.lower() or "110043" in error_msg:
                    print(f"ℹ️ Leverage already set for {symbol}", flush=True)
                    success_count += 1
                else:
                    print(f"⚠️ Failed to set leverage for {symbol}: {e}", flush=True)
        return success_count > 0
    
    def check_existing_positions(self):
        """Check existing positions for all symbols."""
        try:
            all_positions = self.client.get_positions()
            with self.positions_lock:
                for pos in all_positions:
                    symbol = pos.get('symbol', '')
                    size = float(pos.get('size', 0))
                    if size != 0 and symbol:
                        entry_price = float(pos.get('avgPrice', 0))
                        side = 'Buy' if size > 0 else 'Sell'
                        
                        # Calculate fixed TP/SL (matching backtest)
                        tp_sl = self.calculate_fixed_tp_sl(entry_price, side)
                        
                        # Set TP/SL on Bybit if not already set
                        try:
                            self.client.set_tp_sl(symbol, tp_sl['tp_price'], tp_sl['sl_price'])
                            print(f"✓ TP/SL set for existing position: {symbol}", flush=True)
                        except Exception as e:
                            print(f"⚠️ Warning: Could not set TP/SL for {symbol}: {e}", flush=True)
                        
                        self.positions[symbol] = {
                            'position': pos,
                            'entry_price': entry_price,
                            'side': side,
                            'tp_price': tp_sl['tp_price'],
                            'sl_price': tp_sl['sl_price']
                        }
                        print(f"✓ Found existing position: {symbol} {side} @ ${entry_price:.2f}", flush=True)
            
            return len(self.positions) > 0
        except Exception as e:
            print(f"✗ Error checking positions: {e}", flush=True)
            return False
    
    def analyze_coin(self, symbol: str):
        """Analyze a single coin for trading signals."""
        try:
            # Get candlestick data
            df = self.client.get_kline(symbol, self.interval, limit=200)
            
            if len(df) < 50:
                return None
            
            # Check for signal
            signal, signal_data = self.strategy.get_signal(df)
            
            if signal == 'BUY' or signal == 'SELL':
                signal_data['symbol'] = symbol
                signal_data['side'] = signal
                return signal_data
            
            return None
        except Exception as e:
            print(f"✗ Error analyzing {symbol}: {e}", flush=True)
            return None
    
    def analyze_all_coins_parallel(self, symbols: list):
        """Analyze all coins in parallel."""
        signals = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_symbol = {
                executor.submit(self.analyze_coin, symbol): symbol 
                for symbol in symbols
            }
            
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    if result:
                        signals.append(result)
                except Exception as e:
                    print(f"✗ Error analyzing {symbol}: {e}", flush=True)
        
        return signals
    
    def monitor_position_coin(self, symbol: str):
        """Monitor position for a specific coin."""
        with self.positions_lock:
            if symbol not in self.positions:
                return
            
            pos_data = self.positions[symbol]
        
        try:
            current_price = self.client.get_current_price(symbol)
            entry_price = pos_data['entry_price']
            side = pos_data['side']  # Already in "Buy"/"Sell" format
            tp_price = pos_data['tp_price']
            sl_price = pos_data['sl_price']
            
            # Check TP/SL
            should_close = False
            reason = ""
            
            if side == 'Buy':
                if current_price >= tp_price:
                    should_close = True
                    reason = "Take Profit hit"
                elif current_price <= sl_price:
                    should_close = True
                    reason = "Stop Loss hit"
            else:  # Sell
                if current_price <= tp_price:
                    should_close = True
                    reason = "Take Profit hit"
                elif current_price >= sl_price:
                    should_close = True
                    reason = "Stop Loss hit"
            
            if should_close:
                self.close_position_coin(symbol, reason, current_price)
                
        except Exception as e:
            print(f"✗ Error monitoring position for {symbol}: {e}", flush=True)
    
    def monitor_all_positions_parallel(self):
        """Monitor all open positions in parallel."""
        with self.positions_lock:
            symbols = list(self.positions.keys())
        
        if not symbols:
            return
        
        with ThreadPoolExecutor(max_workers=len(symbols)) as executor:
            executor.map(self.monitor_position_coin, symbols)
    
    def get_status_report(self, html_format=True):
        """
        Generate status report with modern Telegram formatting.
        
        Args:
            html_format: If True, return HTML formatted message (default: True)
        
        Returns:
            String containing formatted status report
        """
        try:
            # Get trending coins if not already set
            if not self.trending_coins:
                self.trending_coins = self.get_trending_coins()
            
            # Get current session
            current_session = self.strategy.get_session()
            
            # Session emoji mapping
            session_emoji = {
                'asian': '🌏',
                'european': '🇪🇺',
                'us': '🇺🇸'
            }
            session_emoji_icon = session_emoji.get(current_session.lower(), '📅')
            
            if html_format:
                # Modern HTML formatted message
                lines = []
                
                # Compact header
                lines.append("╔══════════════════════╗")
                lines.append(f"║ 🤖 <b>BOT STATUS</b> ║")
                lines.append("╚══════════════════════╝")
                lines.append("")
                lines.append(f"📊 {session_emoji_icon} {current_session.upper()} • 🎯 {int(self.strategy.signal_threshold*100)}% • 📈 {len(self.trending_coins)} coins")
                lines.append("")
                
                # Coin analysis - collect data with confidence for sorting
                coin_data_list = []
                for symbol in self.trending_coins:
                    try:
                        df = self.client.get_kline(symbol, self.interval, limit=200)
                        df_with_indicators = self.strategy.add_indicators(df)
                        current = df_with_indicators.iloc[-1]
                        
                        session_params = self.strategy.get_session_parameters(current_session)
                        long_strength, short_strength = self.strategy.calculate_signal_strength(
                            df_with_indicators, session_params
                        )
                        
                        if not pd.isna(current['ema_fast']) and not pd.isna(current['ema_slow']):
                            # EMA trend with better visual
                            if current['ema_fast'] > current['ema_medium'] > current['ema_slow']:
                                ema_icon = "📈"
                                ema_text = "BULLISH"
                                ema_color = "🟢"
                            elif current['ema_fast'] < current['ema_medium'] < current['ema_slow']:
                                ema_icon = "📉"
                                ema_text = "BEARISH"
                                ema_color = "🔴"
                            else:
                                ema_icon = "➡️"
                                ema_text = "MIXED"
                                ema_color = "⚪"
                            
                            # Price formatting
                            price = current['close']
                            if price >= 1000:
                                price_str = f"${price:,.0f}"
                            elif price >= 1:
                                price_str = f"${price:.2f}"
                            else:
                                price_str = f"${price:.4f}"
                            
                            # RSI with visual indicator
                            rsi = current['rsi']
                            if rsi > 70:
                                rsi_icon = "🔴"
                            elif rsi < 30:
                                rsi_icon = "🟢"
                            else:
                                rsi_icon = "⚪"
                            
                            # Volume indicator
                            vol_ratio = current['volume_ratio']
                            if vol_ratio > 1.5:
                                vol_icon = "🔥"
                            elif vol_ratio < 0.5:
                                vol_icon = "💤"
                            else:
                                vol_icon = "📊"
                            
                            # Signal strength with modern visual
                            max_strength = max(long_strength, short_strength)
                            threshold = self.strategy.signal_threshold
                            
                            if long_strength > threshold:
                                signal_icon = "🚀"
                                signal_text = f"LONG {int(long_strength*100)}%"
                                bar_length = min(int((long_strength * 8)), 8)
                                signal_bar = "█" * bar_length + "░" * (8 - bar_length)
                            elif short_strength > threshold:
                                signal_icon = "⬇️"
                                signal_text = f"SHORT {int(short_strength*100)}%"
                                bar_length = min(int((short_strength * 8)), 8)
                                signal_bar = "█" * bar_length + "░" * (8 - bar_length)
                            else:
                                conf_pct = int(max_strength * 100)
                                if max_strength >= threshold * 0.8:
                                    signal_icon = "🟡"
                                elif max_strength >= threshold * 0.6:
                                    signal_icon = "🟠"
                                else:
                                    signal_icon = "⚪"
                                signal_text = f"CONF {conf_pct}%"
                                bar_length = min(int((max_strength / threshold * 8)), 8)
                                signal_bar = "▌" * bar_length + "░" * (8 - bar_length)
                            
                            # Compact card format
                            card = (
                                f"┌─ <b>{symbol}</b> ────────────\n"
                                f"│ 💰{price_str} {ema_color}{ema_icon} {ema_text} {rsi_icon}RSI:{rsi:.0f} {vol_icon}VOL:{vol_ratio:.2f}x\n"
                                f"│ {signal_icon} {signal_text} {signal_bar}\n"
                                f"└────────────────────────────"
                            )
                            
                            # Store with confidence for sorting
                            coin_data_list.append({
                                'confidence': max_strength,
                                'symbol': symbol,
                                'card': card
                            })
                        else:
                            # Invalid data - put at end with low confidence
                            card = f"┌─ <b>{symbol}</b> ────────────\n│ ❌ Invalid data\n└────────────────────────────"
                            coin_data_list.append({
                                'confidence': -1,
                                'symbol': symbol,
                                'card': card
                            })
                            
                    except Exception as e:
                        # Error - put at end with low confidence
                        card = f"┌─ <b>{symbol}</b> ────────────\n│ ❌ Error\n└────────────────────────────"
                        coin_data_list.append({
                            'confidence': -1,
                            'symbol': symbol,
                            'card': card
                        })
                
                # Sort by confidence (highest first)
                coin_data_list.sort(key=lambda x: x['confidence'], reverse=True)
                
                # Add sorted coin cards
                for coin_data in coin_data_list:
                    lines.append(coin_data['card'])
                    lines.append("")
                
                lines.append("🔄 <i>Continuous monitoring active</i>")
                lines.append("💡 <i>Send /status to refresh</i>")
                
                return "\n".join(lines), coin_data_list
            else:
                # Plain text format (for logging)
                lines = []
                lines.append(f"🔍 Analyzing {len(self.trending_coins)} coins for signals...")
                lines.append("")
                lines.append("   ➡️ No signals detected - showing detailed analysis...")
                lines.append("")
                lines.append(f"   📅 Current Session: {current_session.upper()}")
                lines.append("")
                
                for symbol in self.trending_coins:
                    try:
                        df = self.client.get_kline(symbol, self.interval, limit=200)
                        df_with_indicators = self.strategy.add_indicators(df)
                        current = df_with_indicators.iloc[-1]
                        
                        session_params = self.strategy.get_session_parameters(current_session)
                        long_strength, short_strength = self.strategy.calculate_signal_strength(
                            df_with_indicators, session_params
                        )
                        
                        if not pd.isna(current['ema_fast']) and not pd.isna(current['ema_slow']):
                            if current['ema_fast'] > current['ema_medium'] > current['ema_slow']:
                                ema_trend = "BULLISH"
                            elif current['ema_fast'] < current['ema_medium'] < current['ema_slow']:
                                ema_trend = "BEARISH"
                            else:
                                ema_trend = "MIXED"
                            
                            max_strength = max(long_strength, short_strength)
                            status_line = f"   {symbol}: ${current['close']:.2f} | EMA:{ema_trend} | RSI:{current['rsi']:.1f} | VOL:{current['volume_ratio']:.2f}x [MAX:{max_strength:.2f}⚪]"
                            lines.append(status_line)
                        else:
                            lines.append(f"   {symbol}: Error - Invalid data")
                            
                    except Exception as e:
                        lines.append(f"   {symbol}: Error - {e}")
                
                lines.append("")
                lines.append("🔄 Continuous monitoring - next check starting immediately...")
                
                return "\n".join(lines)
            
        except Exception as e:
            if html_format:
                return f"❌ Error generating status report: {e}", []
            return f"❌ Error generating status report: {e}"
    
    def get_coin_detail_report(self, symbol: str):
        """
        Get detailed analysis report for a specific coin with chart.
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Tuple of (detail_message, chart_path)
        """
        try:
            # Get kline data
            df = self.client.get_kline(symbol, self.interval, limit=200)
            df_with_indicators = self.strategy.add_indicators(df)
            current = df_with_indicators.iloc[-1]
            
            # Get current session
            current_session = self.strategy.get_session()
            session_params = self.strategy.get_session_parameters(current_session)
            
            # Calculate signal strengths
            long_strength, short_strength = self.strategy.calculate_signal_strength(
                df_with_indicators, session_params
            )
            
            if pd.isna(current['ema_fast']) or pd.isna(current['ema_slow']):
                return "❌ Invalid data for this coin", None
            
            # Format price
            price = current['close']
            if price >= 1000:
                price_str = f"${price:,.0f}"
            elif price >= 1:
                price_str = f"${price:.2f}"
            else:
                price_str = f"${price:.4f}"
            
            # EMA trend
            if current['ema_fast'] > current['ema_medium'] > current['ema_slow']:
                ema_text = "🟢 📈 BULLISH"
            elif current['ema_fast'] < current['ema_medium'] < current['ema_slow']:
                ema_text = "🔴 📉 BEARISH"
            else:
                ema_text = "⚪ ➡️ MIXED"
            
            # RSI
            rsi = current['rsi']
            if rsi > 70:
                rsi_status = "🔴 Overbought"
            elif rsi < 30:
                rsi_status = "🟢 Oversold"
            else:
                rsi_status = "⚪ Neutral"
            
            # Volume
            vol_ratio = current['volume_ratio']
            if vol_ratio > 1.5:
                vol_status = "🔥 High"
            elif vol_ratio < 0.5:
                vol_status = "💤 Low"
            else:
                vol_status = "📊 Normal"
            
            # Signal
            max_strength = max(long_strength, short_strength)
            threshold = self.strategy.signal_threshold
            
            if long_strength > threshold:
                signal_text = f"🚀 LONG {int(long_strength*100)}%"
            elif short_strength > threshold:
                signal_text = f"⬇️ SHORT {int(short_strength*100)}%"
            else:
                conf_pct = int(max_strength * 100)
                if max_strength >= threshold * 0.8:
                    signal_text = f"🟡 CONF {conf_pct}%"
                elif max_strength >= threshold * 0.6:
                    signal_text = f"🟠 CONF {conf_pct}%"
                else:
                    signal_text = f"⚪ CONF {conf_pct}%"
            
            # Generate detail message
            lines = []
            lines.append(f"╔═══════════════════════════════╗")
            lines.append(f"║  📊 <b>{symbol} DETAIL</b>  ║")
            lines.append(f"╚═══════════════════════════════╝")
            lines.append("")
            lines.append(f"💰 <b>Price:</b> <code>{price_str}</code>")
            lines.append(f"{ema_text}")
            lines.append(f"")
            lines.append(f"📈 <b>Indicators:</b>")
            lines.append(f"  • RSI: <code>{rsi:.1f}</code> {rsi_status}")
            lines.append(f"  • Volume Ratio: <code>{vol_ratio:.2f}x</code> {vol_status}")
            lines.append(f"  • EMA Fast: <code>${current['ema_fast']:.2f}</code>")
            lines.append(f"  • EMA Medium: <code>${current['ema_medium']:.2f}</code>")
            lines.append(f"  • EMA Slow: <code>${current['ema_slow']:.2f}</code>")
            if 'bb_upper' in current and not pd.isna(current['bb_upper']):
                lines.append(f"  • BB Upper: <code>${current['bb_upper']:.2f}</code>")
                lines.append(f"  • BB Lower: <code>${current['bb_lower']:.2f}</code>")
            lines.append("")
            lines.append(f"🎯 <b>Signal Analysis:</b>")
            lines.append(f"  • {signal_text}")
            lines.append(f"  • Long Strength: <code>{int(long_strength*100)}%</code>")
            lines.append(f"  • Short Strength: <code>{int(short_strength*100)}%</code>")
            lines.append(f"  • Session: <code>{current_session.upper()}</code>")
            lines.append("")
            lines.append("📊 <i>Chart analysis attached below</i>")
            
            detail_message = "\n".join(lines)
            
            # Generate chart
            chart_path = self.chart_generator.generate_analysis_chart(
                df_with_indicators, symbol, price,
                current['ema_fast'], current['ema_medium'], current['ema_slow'],
                rsi, current.get('bb_upper', 0), current.get('bb_middle', 0),
                current.get('bb_lower', 0), long_strength, short_strength,
                current_session
            )
            
            return detail_message, chart_path
            
        except Exception as e:
            return f"❌ Error getting detail for {symbol}: {str(e)}", None
    
    def close_position_coin(self, symbol: str, reason: str, exit_price: float):
        """Close position for a specific coin."""
        with self.positions_lock:
            if symbol not in self.positions:
                return
            
            pos_data = self.positions[symbol]
            entry_price = pos_data['entry_price']
            side = pos_data['side']
            tp_price = pos_data['tp_price']
            sl_price = pos_data['sl_price']
            position = pos_data['position']
        
        try:
            print(f"Closing position {symbol}: {reason}", flush=True)
            
            # Close position on exchange
            self.client.close_position(symbol, side)
            
            # Calculate PnL
            if side == 'Buy':
                pnl = (exit_price - entry_price) * abs(float(position.get('size', 0)))
                pnl_percent = ((exit_price - entry_price) / entry_price) * 100
            else:  # Sell
                pnl = (entry_price - exit_price) * abs(float(position.get('size', 0)))
                pnl_percent = ((entry_price - exit_price) / entry_price) * 100
            
            # Get chart data
            df = self.client.get_kline(symbol, self.interval, limit=200)
            exit_df = self.strategy.add_indicators(df)
            chart_path = self.chart_generator.generate_exit_chart(
                exit_df, entry_price, exit_price,
                tp_price, sl_price, symbol,
                side, pnl, pnl_percent
            )
            
            # Send notification
            self.notifier.send_exit_sync(
                symbol, side, entry_price,
                exit_price, tp_price, sl_price,
                pnl, pnl_percent, reason, chart_path
            )
            
            # Remove position
            with self.positions_lock:
                if symbol in self.positions:
                    del self.positions[symbol]
            
            print(f"✓ Position closed: {symbol} {reason}", flush=True)
            
        except Exception as e:
            print(f"✗ Error closing position {symbol}: {e}", flush=True)
            self.notifier.send_error_sync(f"Error closing position {symbol}: {e}")
    
    def execute_trade_coin(self, signal_data: dict):
        """Execute trade for a specific coin."""
        symbol = signal_data['symbol']
        side_str = signal_data.get('side', 'Buy')
        entry_price = signal_data.get('entry_price')
        
        # Convert side to Bybit format: "Buy" or "Sell" (capitalized)
        side = 'Buy' if side_str.upper() == 'BUY' else 'Sell'
        
        # Check if we already have a position for this coin
        with self.positions_lock:
            if symbol in self.positions:
                print(f"Already have position for {symbol}, skipping entry", flush=True)
                return
        
        try:
            # Get minimum order size and minimum order value for this symbol
            min_qty, qty_step, min_order_value = self.client.get_minimum_order_size(symbol)
            
            # Calculate position size
            balance_info = self.client.get_wallet_balance()
            try:
                available_balance = float(balance_info['list'][0]['coin'][0]['availableToWithdraw'])
                # Use configured percentage per position (matches backtest: 20%)
                position_value = available_balance * Config.POSITION_SIZE_PCT * self.leverage
                calculated_qty = position_value / entry_price
            except:
                # Fallback: calculate based on minimum order value
                calculated_qty = min_order_value / entry_price
            
            # Ensure order value meets minimum (quantity * price >= min_order_value)
            min_qty_by_value = min_order_value / entry_price
            if calculated_qty < min_qty_by_value:
                calculated_qty = min_qty_by_value
                print(f"   Adjusted quantity to meet minimum order value: {calculated_qty:.8f}", flush=True)
            
            # Ensure quantity meets minimum requirement
            if calculated_qty < min_qty:
                calculated_qty = min_qty
            
            # Round to qty_step precision using floor to ensure we don't exceed
            if qty_step > 0:
                import math
                calculated_qty = math.floor(calculated_qty / qty_step) * qty_step
                # Ensure still meets minimum after rounding down
                if calculated_qty < min_qty:
                    calculated_qty = min_qty
                
                # Re-check minimum order value after rounding
                order_value = calculated_qty * entry_price
                if order_value < min_order_value:
                    # Round up to meet minimum order value
                    required_qty = min_order_value / entry_price
                    calculated_qty = math.ceil(required_qty / qty_step) * qty_step
            
            # Format quantity - use precision based on qty_step
            # For Bybit, quantity should be formatted according to qty_step
            if qty_step >= 1:
                qty = str(int(calculated_qty))
            elif qty_step >= 0.1:
                qty = f"{calculated_qty:.1f}".rstrip('0').rstrip('.')
            elif qty_step >= 0.01:
                qty = f"{calculated_qty:.2f}".rstrip('0').rstrip('.')
            elif qty_step >= 0.001:
                qty = f"{calculated_qty:.3f}".rstrip('0').rstrip('.')
            else:
                # For very small steps, use up to 8 decimals
                qty = f"{calculated_qty:.8f}".rstrip('0').rstrip('.')
            
            # Final verification
            order_value = float(qty) * entry_price
            print(f"   Order size: {qty} (min_qty: {min_qty}, step: {qty_step}, min_value: {min_order_value} USDT)", flush=True)
            print(f"   Order value: ${order_value:.2f} USDT", flush=True)
            
            if order_value < min_order_value:
                raise Exception(f"Order value ${order_value:.2f} is below minimum ${min_order_value:.2f} USDT")
            
            # Place order
            order_result = self.client.place_order(
                symbol=symbol,
                side=side,  # Now using "Buy" or "Sell"
                order_type="Market",
                qty=qty
            )
            
            print(f"✓ Order placed: {side} {qty} {symbol} @ Market", flush=True)
            
            # Wait a moment for position to be registered
            time.sleep(1)
            
            # Calculate fixed TP/SL (matching backtest)
            tp_sl = self.calculate_fixed_tp_sl(entry_price, side)
            
            # Get current position
            positions = self.client.get_positions(symbol)
            position = positions[0] if positions else None
            
            # Set TP/SL on Bybit exchange
            try:
                self.client.set_tp_sl(symbol, tp_sl['tp_price'], tp_sl['sl_price'])
                print(f"✓ TP/SL set: TP=${tp_sl['tp_price']:.2f}, SL=${tp_sl['sl_price']:.2f}", flush=True)
            except Exception as e:
                print(f"⚠️ Warning: Could not set TP/SL on exchange: {e}", flush=True)
                # Continue anyway, we'll monitor manually
            
            # Store position data
            with self.positions_lock:
                self.positions[symbol] = {
                    'position': position,
                    'entry_price': entry_price,
                    'side': side,
                    'tp_price': tp_sl['tp_price'],
                    'sl_price': tp_sl['sl_price']
                }
            
            # Generate entry chart
            df = self.client.get_kline(symbol, self.interval, limit=200)
            entry_df = self.strategy.add_indicators(df)
            chart_path = self.chart_generator.generate_entry_chart(
                entry_df, entry_price, tp_sl['tp_price'], tp_sl['sl_price'],
                signal_data.get('ema_fast', 0), signal_data.get('ema_slow', 0),
                symbol, side, self.leverage
            )
            
            # Send notification
            self.notifier.send_entry_sync(
                symbol, side, entry_price,
                tp_sl['tp_price'], tp_sl['sl_price'], self.leverage,
                chart_path
            )
            
        except Exception as e:
            print(f"✗ Error executing trade for {symbol}: {e}", flush=True)
            self.notifier.send_error_sync(f"Error executing trade for {symbol}: {e}")
    
    
    def run(self):
        """Main bot loop with parallel multi-coin analysis."""
        print(f"\n🚀 Starting trading bot...", flush=True)
        print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", flush=True)
        
        # Get trending coins
        self.trending_coins = self.get_trending_coins()
        
        # Setup leverage for all coins
        if not self.setup_leverage_for_all_coins(self.trending_coins):
            print("⚠️ Continuing without leverage setup...", flush=True)
        
        # Check for existing positions
        self.check_existing_positions()
        
        # Start Telegram command handler
        self.command_handler.start()
        
        print("🔄 Entering main trading loop...", flush=True)
        print(f"📊 Analyzing {len(self.trending_coins)} coins in parallel", flush=True)
        
        # Main loop
        iteration = 0
        while True:
            try:
                iteration += 1
                print(f"\n{'='*60}", flush=True)
                print(f"[{iteration}] Starting analysis cycle...", flush=True)
                print(f"{'='*60}", flush=True)
                
                # Monitor existing positions in parallel
                with self.positions_lock:
                    active_positions = len(self.positions)
                
                if active_positions > 0:
                    print(f"📊 Monitoring {active_positions} active positions...", flush=True)
                    self.monitor_all_positions_parallel()
                
                # Analyze all coins in parallel for new signals
                print(f"🔍 Analyzing {len(self.trending_coins)} coins for signals...", flush=True)
                signals = self.analyze_all_coins_parallel(self.trending_coins)
                
                if signals:
                    print(f"🚨 Found {len(signals)} signal(s)!", flush=True)
                    for signal in signals:
                        symbol = signal.get('symbol', 'Unknown')
                        side = signal.get('side', 'Unknown')
                        entry_price = signal.get('entry_price', 0)
                        print(f"   - {symbol}: {side} @ ${entry_price:.2f}", flush=True)
                        self.execute_trade_coin(signal)
                else:
                    print("   ➡️ No signals detected - showing detailed analysis...", flush=True)
                    
                    # Get current session
                    current_session = self.strategy.get_session()
                    print(f"   📅 Current Session: {current_session.upper()}", flush=True)
                    
                    # Show detailed status for first few coins
                    for i, symbol in enumerate(self.trending_coins[:5]):
                        try:
                            df = self.client.get_kline(symbol, self.interval, limit=200)
                            df_with_indicators = self.strategy.add_indicators(df)
                            current = df_with_indicators.iloc[-1]
                            
                            # Get session parameters
                            session_params = self.strategy.get_session_parameters(current_session)
                            
                            # Calculate signal strengths
                            long_strength, short_strength = self.strategy.calculate_signal_strength(
                                df_with_indicators, session_params
                            )
                            
                            if not pd.isna(current['ema_fast']) and not pd.isna(current['ema_slow']):
                                # EMA alignment
                                ema_trend = ""
                                if current['ema_fast'] > current['ema_medium'] > current['ema_slow']:
                                    ema_trend = "BULLISH"
                                elif current['ema_fast'] < current['ema_medium'] < current['ema_slow']:
                                    ema_trend = "BEARISH"
                                else:
                                    ema_trend = "MIXED"
                                
                                # Signal strength indicator
                                signal_str = ""
                                if long_strength > self.strategy.signal_threshold:
                                    signal_str = f" [LONG:{long_strength:.2f}🟢]"
                                elif short_strength > self.strategy.signal_threshold:
                                    signal_str = f" [SHORT:{short_strength:.2f}🔴]"
                                else:
                                    max_strength = max(long_strength, short_strength)
                                    signal_str = f" [MAX:{max_strength:.2f}⚪]"
                                
                                print(f"   {symbol}: ${current['close']:.2f} | EMA:{ema_trend} | RSI:{current['rsi']:.1f} | VOL:{current['volume_ratio']:.2f}x{signal_str}", flush=True)
                        except Exception as e:
                            print(f"   {symbol}: Error - {e}", flush=True)
                
                # Continue immediately to next iteration (no delay)
                print(f"✓ Analysis cycle completed, starting next cycle...", flush=True)
                
            except KeyboardInterrupt:
                print("\n⚠️ Bot stopped by user", flush=True)
                break
            except Exception as e:
                print(f"✗ Error in main loop: {e}", flush=True)
                traceback.print_exc()
                self.notifier.send_error_sync(f"Error in main loop: {e}")
                time.sleep(60)
        
        # Stop command handler
        self.command_handler.stop()


def main():
    """Main entry point."""
    try:
        print("=" * 50, flush=True)
        print("Bybit Trading Bot Starting...", flush=True)
        print("=" * 50, flush=True)
        
        bot = TradingBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n⚠️ Bot stopped by user", flush=True)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

