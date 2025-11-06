"""Telegram command handler for interactive commands."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import TelegramError
import asyncio
import threading
import os
from config import Config


class TelegramCommandHandler:
    """Handle Telegram commands like /status."""
    
    def __init__(self, trading_bot):
        """
        Initialize Telegram command handler.
        
        Args:
            trading_bot: Instance of TradingBot
        """
        self.trading_bot = trading_bot
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.application = None
        self.running = False
        self.thread = None
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        # Check if message is from authorized chat
        if str(update.effective_chat.id) != str(self.chat_id):
            await update.message.reply_text("❌ Unauthorized access.")
            return
        
        try:
            # Show typing indicator
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action='typing'
            )
            
            # Send initial message
            processing_msg = await update.message.reply_text(
                "⏳ Generating status report... Please wait.",
                parse_mode='HTML'
            )
            
            # Run status report generation in executor to prevent blocking
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Run blocking operations in executor with timeout (60 seconds)
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        self.trading_bot.get_status_report,
                        True  # html_format=True
                    ),
                    timeout=60.0
                )
            except asyncio.TimeoutError:
                await processing_msg.edit_text(
                    "⏱️ <b>Timeout</b>\n\nStatus report generation took too long. Please try again later.",
                    parse_mode='HTML'
                )
                return
            
            if isinstance(result, tuple):
                status_report, coin_data_list = result
            else:
                status_report = result
                coin_data_list = []
            
            # Create inline keyboard buttons for each coin
            keyboard = []
            if coin_data_list:
                # Group buttons in rows of 2
                for i in range(0, len(coin_data_list), 2):
                    row = []
                    for j in range(2):
                        if i + j < len(coin_data_list):
                            coin_data = coin_data_list[i + j]
                            symbol = coin_data.get('symbol', '')
                            if symbol:
                                row.append(InlineKeyboardButton(symbol, callback_data=f"detail_{symbol}"))
                    if row:
                        keyboard.append(row)
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            # Delete processing message and send status report
            try:
                await processing_msg.delete()
            except:
                pass
            
            # Send status report with HTML formatting and buttons
            await update.message.reply_text(
                status_report,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            import traceback
            error_msg = f"❌ <b>Error getting status:</b>\n<code>{str(e)[:200]}</code>"
            try:
                await update.message.reply_text(error_msg, parse_mode='HTML')
            except:
                pass
            print(f"Error in status_command: {e}", flush=True)
            traceback.print_exc()
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        if str(update.effective_chat.id) != str(self.chat_id):
            await update.message.reply_text("❌ Unauthorized access.")
            return
        
        welcome_msg = """
🤖 <b>Trading Bot Commands</b>

/status - Get current trading status and coin analysis
/start - Show this help message

Bot is running and monitoring the market.
"""
        await update.message.reply_text(welcome_msg, parse_mode='HTML')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callback queries."""
        query = update.callback_query
        
        # Answer callback immediately to prevent timeout
        await query.answer("⏳ Generating analysis...")
        
        # Check if message is from authorized chat
        if str(query.message.chat.id) != str(self.chat_id):
            await query.edit_message_text("❌ Unauthorized access.")
            return
        
        try:
            # Show typing indicator
            await context.bot.send_chat_action(
                chat_id=query.message.chat.id,
                action='typing'
            )
            
            # Parse callback data
            if query.data.startswith("detail_"):
                symbol = query.data.replace("detail_", "")
                
                # Send initial message to show we're processing
                processing_msg = await query.message.reply_text(
                    f"⏳ Analyzing <b>{symbol}</b>... Please wait.",
                    parse_mode='HTML'
                )
                
                # Run chart generation in executor to prevent blocking
                import asyncio
                loop = asyncio.get_event_loop()
                
                # Run blocking operations in executor with timeout (30 seconds)
                try:
                    detail_message, chart_path = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            self.trading_bot.get_coin_detail_report,
                            symbol
                        ),
                        timeout=30.0
                    )
                except asyncio.TimeoutError:
                    await query.message.reply_text(
                        f"⏱️ <b>Timeout</b>\n\nAnalysis for <b>{symbol}</b> took too long. Please try again later.",
                        parse_mode='HTML'
                    )
                    return
                
                # Delete processing message
                try:
                    await processing_msg.delete()
                except:
                    pass
                
                if chart_path and os.path.exists(chart_path):
                    # Send photo with caption
                    try:
                        with open(chart_path, 'rb') as photo:
                            await query.message.reply_photo(
                                photo=photo,
                                caption=detail_message,
                                parse_mode='HTML'
                            )
                    finally:
                        # Clean up
                        if os.path.exists(chart_path):
                            try:
                                os.remove(chart_path)
                            except:
                                pass
                else:
                    await query.message.reply_text(detail_message, parse_mode='HTML')
            
        except Exception as e:
            import traceback
            symbol = query.data.replace("detail_", "") if query.data.startswith("detail_") else "coin"
            error_msg = f"❌ <b>Error analyzing {symbol}:</b>\n<code>{str(e)[:200]}</code>"
            try:
                await query.message.reply_text(error_msg, parse_mode='HTML')
            except:
                pass
            print(f"Error in button_callback: {e}", flush=True)
            traceback.print_exc()
    
    def _run_bot(self):
        """Run the Telegram bot in a separate event loop."""
        async def main():
            # Create application
            self.application = Application.builder().token(self.bot_token).build()
            
            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            
            # Add callback query handler for buttons
            self.application.add_handler(CallbackQueryHandler(self.button_callback))
            
            print("✓ Telegram command handler started", flush=True)
            print(f"  Listening for commands in chat: {self.chat_id}", flush=True)
            
            # Initialize and start
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(drop_pending_updates=True)
            
            # Keep running until stopped
            while self.running:
                await asyncio.sleep(0.5)
            
            # Stop polling
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(main())
        except Exception as e:
            print(f"✗ Error in Telegram command handler: {e}", flush=True)
            import traceback
            traceback.print_exc()
        finally:
            try:
                loop.close()
            except:
                pass
    
    def start(self):
        """Start the Telegram command handler in a separate thread."""
        if self.running:
            print("⚠️ Telegram command handler already running", flush=True)
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_bot, daemon=True)
        self.thread.start()
        print("✓ Starting Telegram command handler...", flush=True)
    
    def stop(self):
        """Stop the Telegram command handler."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        print("✓ Telegram command handler stopped", flush=True)

