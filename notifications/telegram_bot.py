"""Telegram notification handler."""
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
import asyncio
import os
import time
from config import Config


class TelegramNotifier:
    """Handle Telegram notifications with chart images."""
    
    def __init__(self):
        """Initialize Telegram bot."""
        self.bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
        self.chat_id = Config.TELEGRAM_CHAT_ID
        # Rate limiting untuk error notifications
        # Format: {error_key: last_sent_timestamp}
        self.error_notifications = {}
        self.error_cooldown_seconds = 600  # 10 menit cooldown untuk error yang sama
    
    def _run_async(self, coro):
        """Run async function in a new event loop."""
        try:
            # Try to get existing loop
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Loop is closed")
        except RuntimeError:
            # Create new event loop if none exists or is closed
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            return loop.run_until_complete(coro)
        finally:
            # Don't close the loop, just let it be reused
            pass
    
    async def send_message(self, message: str, reply_markup=None):
        """Send text message to Telegram."""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return True
        except TelegramError as e:
            print(f"Error sending Telegram message: {e}")
            return False
    
    async def send_photo(self, photo_path: str, caption: str = None, reply_markup=None):
        """Send photo with caption to Telegram."""
        try:
            with open(photo_path, 'rb') as photo:
                await self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=photo,
                    caption=caption,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
            
            # Clean up image file after sending
            if os.path.exists(photo_path):
                os.remove(photo_path)
            
            return True
        except TelegramError as e:
            print(f"Error sending Telegram photo: {e}")
            return False
        except FileNotFoundError:
            print(f"Photo file not found: {photo_path}")
            return False
    
    def _create_status_button(self):
        """Create inline keyboard button for /status command."""
        keyboard = [[InlineKeyboardButton("📊 Status", callback_data="status")]]
        return InlineKeyboardMarkup(keyboard)
    
    async def notify_entry(self, symbol: str, side: str, entry_price: float,
                          tp_price: float, sl_price: float, leverage: int,
                          chart_path: str):
        """Send entry notification with chart."""
        message = f"""
🚀 <b>ENTRY SIGNAL</b>

📊 <b>Symbol:</b> {symbol}
📈 <b>Side:</b> {side.upper()}
💰 <b>Entry Price:</b> ${entry_price:.2f}
🎯 <b>Take Profit:</b> ${tp_price:.2f} (+1%)
🛑 <b>Stop Loss:</b> ${sl_price:.2f} (-1%)
⚡ <b>Leverage:</b> {leverage}x

Chart analysis attached below.
"""
        
        reply_markup = self._create_status_button()
        await self.send_photo(chart_path, caption=message, reply_markup=reply_markup)
    
    async def notify_exit(self, symbol: str, side: str, entry_price: float,
                         exit_price: float, tp_price: float, sl_price: float,
                         pnl: float, pnl_percent: float, exit_reason: str,
                         chart_path: str):
        """Send exit notification with chart."""
        pnl_sign = '+' if pnl >= 0 else ''
        emoji = '✅' if pnl >= 0 else '❌'
        
        message = f"""
{emoji} <b>POSITION CLOSED</b>

📊 <b>Symbol:</b> {symbol}
📈 <b>Side:</b> {side.upper()}
💰 <b>Entry Price:</b> ${entry_price:.2f}
💰 <b>Exit Price:</b> ${exit_price:.2f}
🎯 <b>Take Profit:</b> ${tp_price:.2f}
🛑 <b>Stop Loss:</b> ${sl_price:.2f}
📉 <b>PnL:</b> {pnl_sign}${pnl:.2f} ({pnl_sign}{pnl_percent:.2f}%)
🔔 <b>Reason:</b> {exit_reason}

Chart analysis attached below.
"""
        
        reply_markup = self._create_status_button()
        await self.send_photo(chart_path, caption=message, reply_markup=reply_markup)
    
    async def notify_error(self, error_message: str):
        """Send error notification."""
        message = f"""
⚠️ <b>ERROR OCCURRED</b>

{error_message}

Please check the bot logs for more details.
"""
        reply_markup = self._create_status_button()
        await self.send_message(message, reply_markup=reply_markup)
    
    def send_entry_sync(self, symbol: str, side: str, entry_price: float,
                       tp_price: float, sl_price: float, leverage: int,
                       chart_path: str):
        """Synchronous wrapper for entry notification."""
        try:
            self._run_async(self.notify_entry(symbol, side, entry_price, tp_price, 
                                             sl_price, leverage, chart_path))
        except Exception as e:
            print(f"Failed to send Telegram entry notification: {e}", flush=True)
    
    def send_exit_sync(self, symbol: str, side: str, entry_price: float,
                      exit_price: float, tp_price: float, sl_price: float,
                      pnl: float, pnl_percent: float, exit_reason: str,
                      chart_path: str):
        """Synchronous wrapper for exit notification."""
        try:
            self._run_async(self.notify_exit(symbol, side, entry_price, exit_price,
                                            tp_price, sl_price, pnl, pnl_percent,
                                            exit_reason, chart_path))
        except Exception as e:
            print(f"Failed to send Telegram exit notification: {e}", flush=True)
    
    def send_error_sync(self, error_message: str):
        """Synchronous wrapper for error notification with rate limiting."""
        try:
            # Create error key untuk deduplication (ambil 100 karakter pertama)
            error_key = error_message[:100] if len(error_message) > 100 else error_message
            
            # Check rate limiting
            current_time = time.time()
            last_sent = self.error_notifications.get(error_key, 0)
            
            if current_time - last_sent < self.error_cooldown_seconds:
                # Masih dalam cooldown, skip notifikasi
                remaining_time = int(self.error_cooldown_seconds - (current_time - last_sent))
                print(f"⚠️ Error notification suppressed (cooldown: {remaining_time}s): {error_key[:50]}...", flush=True)
                return
            
            # Update timestamp dan kirim notifikasi
            self.error_notifications[error_key] = current_time
            
            # Cleanup old entries (lebih dari 1 jam)
            cutoff_time = current_time - 3600
            self.error_notifications = {
                k: v for k, v in self.error_notifications.items() 
                if v > cutoff_time
            }
            
            self._run_async(self.notify_error(error_message))
        except Exception as e:
            print(f"Failed to send Telegram error notification: {e}", flush=True)
