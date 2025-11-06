# 🔧 CRITICAL: Update Your .env File

## ⚠️ Action Required

Your `.env` file currently has `LEVERAGE=10`, but the backtest uses `LEVERAGE=5`.

To match backtest configuration **exactly**, you need to update your `.env` file.

---

## 📝 Steps to Update

### 1. Edit .env File

```bash
nano .env
# or
vim .env
```

### 2. Find and Change This Line

**FROM:**
```bash
LEVERAGE=10
```

**TO:**
```bash
LEVERAGE=5
```

### 3. Save and Restart Bot

```bash
# Save the file (Ctrl+O, Enter, Ctrl+X for nano)

# Restart bot
docker-compose restart
```

---

## ✅ Verify Changes

After restart, check logs:

```bash
docker-compose logs --tail=20 | grep "Leverage set"
```

**Should show:**
```
✓ Leverage set to 5x for BTCUSDT
✓ Leverage set to 5x for ETHUSDT
... etc
```

---

## 📊 What Changed

### Before (Your Current Setup)
- **Leverage**: 10x
- **Position Size**: 5% per coin
- **Risk**: Higher leverage = higher risk

### After (Matching Backtest)
- **Leverage**: 5x ✅
- **Position Size**: 20% per position ✅
- **Risk**: Better risk management

---

## 🎯 Why This Matters

The backtest that showed **+1,250% profit** used:
- 5x leverage
- 20% position sizing
- 15-minute timeframe

For accurate performance comparison, your live bot must use **identical parameters**.

---

## 📋 Complete .env Configuration

Your `.env` should have these values (matching backtest):

```bash
# Bybit API (your existing values)
BYBIT_API_KEY=your_api_key_here
BYBIT_API_SECRET=your_api_secret_here

# Telegram (your existing values)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Trading Configuration (CRITICAL - Must Match Backtest)
LEVERAGE=5
TRADING_PAIR=BTCUSDT
ENVIRONMENT=demo
INTERVAL=15

# SessionAware Strategy (Optional - defaults are already optimal)
STRATEGY_EMA_FAST=8
STRATEGY_EMA_MEDIUM=21
STRATEGY_EMA_SLOW=50
STRATEGY_SIGNAL_THRESHOLD=0.70
```

---

## ⚡ Quick Fix Command

```bash
# Stop bot
docker-compose down

# Edit .env (change LEVERAGE=10 to LEVERAGE=5)
nano .env

# Restart bot
docker-compose up -d

# Verify
docker-compose logs --tail=20 | grep Leverage
```

---

## 🚨 Important Notes

1. **Demo Mode First**: Test with `ENVIRONMENT=demo` before real trading
2. **Position Sizing**: Now uses 20% (was 5%), so:
   - Max 5 concurrent positions = 100% balance exposure
   - More aggressive than before
   - Monitor carefully
3. **Backtest Alignment**: All parameters now match backtest exactly

---

## 📈 Expected Results After Update

With correct configuration:
- Leverage: 5x ✅
- Position size: 20% per position ✅
- Timeframe: 15 minutes ✅
- Strategy: SessionAware ✅
- Parameters: All matched ✅

Your bot will now trade with **identical parameters** to the profitable backtest!

---

**Please update your .env file now and restart the bot.**

