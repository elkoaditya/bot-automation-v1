# TP/SL Alignment Fix: Bot Now Matches Backtest

## Summary

Bot telah diupdate untuk menggunakan **fixed TP/SL** yang sama seperti backtest, memastikan consistency antara backtest results dan bot behavior.

---

## Changes Made

### 1. Added Fixed TP/SL Constants (bot.py)

```python
# Fixed TP/SL (matching backtest config)
self.stop_loss_pct = 0.025   # 2.5% stop loss (matches backtest)
self.take_profit_pct = 0.05  # 5.0% take profit (matches backtest)
```

**Values match backtest config:**
```python
# backtest/config.py
DEFAULT_STOP_LOSS = 0.025   # 2.5%
DEFAULT_TAKE_PROFIT = 0.05  # 5.0%
```

### 2. Created Fixed TP/SL Calculation Method

```python
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
```

### 3. Updated check_existing_positions()

**Before:**
```python
# Calculate TP/SL (SessionAware uses dynamic ATR-based TP/SL)
tp_sl = self.strategy.calculate_tp_sl(entry_price, side)
```

**After:**
```python
# Calculate fixed TP/SL (matching backtest)
tp_sl = self.calculate_fixed_tp_sl(entry_price, side)
```

### 4. Updated execute_trade_coin()

**Before:**
```python
# Calculate TP/SL using ATR and session data from signal
atr_pct = signal_data.get('atr_pct')
session = signal_data.get('session')
tp_sl = self.strategy.calculate_tp_sl(
    entry_price, side, atr_pct=atr_pct, session=session
)
```

**After:**
```python
# Calculate fixed TP/SL (matching backtest)
tp_sl = self.calculate_fixed_tp_sl(entry_price, side)
```

### 5. Removed Session-Specific Notification Info

Removed session-aware details from notifications since TP/SL is now fixed:
- Removed session info
- Removed signal strength specific to session
- Kept basic signal information

---

## Before vs After Comparison

### Before (Dynamic TP/SL)

| Session | Stop Loss | Take Profit | Risk:Reward |
|---------|-----------|-------------|-------------|
| Asian | ATR × 1.0 (varies) | SL × 1.5 | 1:1.5 |
| European | ATR × 1.5 (varies) | SL × 2.0 | 1:2.0 |
| US | ATR × 2.0 (varies) | SL × 2.5 | 1:2.5 |

**Issues:**
- ❌ Different from backtest
- ❌ Backtest results not representative
- ❌ ATR-based (varies with volatility)

### After (Fixed TP/SL)

| Session | Stop Loss | Take Profit | Risk:Reward |
|---------|-----------|-------------|-------------|
| ALL | 2.5% (fixed) | 5.0% (fixed) | 1:2.0 |

**Benefits:**
- ✅ Matches backtest exactly
- ✅ Backtest results now representative
- ✅ Consistent behavior across all sessions
- ✅ Predictable risk management

---

## Example Scenarios

### BTCUSDT @ $50,000

#### Before (Dynamic)
| Session | SL Price | TP Price | SL % | TP % |
|---------|----------|----------|------|------|
| Asian (ATR=$500) | $49,500 | $49,750 | 1.0% | 1.5% |
| European (ATR=$500) | $49,250 | $51,500 | 1.5% | 3.0% |
| US (ATR=$500) | $49,000 | $52,500 | 2.0% | 5.0% |

#### After (Fixed)
| Session | SL Price | TP Price | SL % | TP % |
|---------|----------|----------|------|------|
| ALL | $48,750 | $52,500 | 2.5% | 5.0% |

---

## Verification Checklist

### ✅ TP/SL Calculation
- [x] Bot uses fixed 2.5% SL
- [x] Bot uses fixed 5.0% TP
- [x] Backtest uses fixed 2.5% SL
- [x] Backtest uses fixed 5.0% TP
- [x] Values match exactly

### ✅ Signal Logic (Still Aligned)
- [x] Session detection identical
- [x] Signal strength calculation identical
- [x] Entry filters identical
- [x] Technical indicators identical

### ✅ Code Updates
- [x] Added self.stop_loss_pct = 0.025
- [x] Added self.take_profit_pct = 0.05
- [x] Created calculate_fixed_tp_sl() method
- [x] Updated check_existing_positions()
- [x] Updated execute_trade_coin()
- [x] Removed dynamic session TP/SL logic
- [x] Cleaned up notification messages

---

## Impact on Strategy

### What Remains from SessionAware

The bot STILL uses SessionAware strategy for:
- ✅ Signal generation (session-aware thresholds)
- ✅ RSI levels per session
- ✅ Volume filters per session
- ✅ Trend vs mean reversion bias per session
- ✅ Signal strength calculation

### What Changed

Only TP/SL execution:
- ❌ No longer uses dynamic ATR-based TP/SL
- ✅ Uses fixed 2.5% / 5.0% like backtest

This means:
- Signals are still session-aware and adaptive
- But risk management is now consistent and matches backtest

---

## Testing Notes

### Expected Behavior

1. **All Sessions Use Same TP/SL:**
   - Asian session: 2.5% SL, 5.0% TP
   - European session: 2.5% SL, 5.0% TP
   - US session: 2.5% SL, 5.0% TP

2. **Entry Signals Still Session-Aware:**
   - Different RSI thresholds per session
   - Different volume requirements per session
   - Different trend/MR bias per session

3. **Bot Logs Show Fixed Values:**
   ```
   ✓ Bot initialized
     Leverage: 5x
     Interval: 15m
     Environment: demo
     Stop Loss: 2.5%
     Take Profit: 5.0%
   ```

---

## Backtest Alignment Status

| Component | Backtest | Bot | Status |
|-----------|----------|-----|--------|
| Signal Logic | SessionAware | SessionAware | ✅ ALIGNED |
| Entry Filters | SessionAware | SessionAware | ✅ ALIGNED |
| Stop Loss | Fixed 2.5% | Fixed 2.5% | ✅ ALIGNED |
| Take Profit | Fixed 5.0% | Fixed 5.0% | ✅ ALIGNED |
| Risk:Reward | 1:2.0 | 1:2.0 | ✅ ALIGNED |
| Leverage | 5x | 5x | ✅ ALIGNED |
| Position Size | 20% | 20% | ✅ ALIGNED |

**✅ ALL COMPONENTS NOW ALIGNED!**

---

## Recommendations

### For Production

1. **Monitor TP/SL Hit Rates:**
   - Track how often 2.5% SL is hit
   - Track how often 5.0% TP is hit
   - Compare with backtest statistics

2. **Consider Session-Specific Adjustments (Future):**
   - If fixed TP/SL underperforms, consider:
     - Tighter stops for Asian (1.5%)
     - Wider stops for US (3.5%)
   - But update BOTH backtest and bot together

3. **Backtest Results Now Valid:**
   - Use backtest metrics for decision making
   - Expected win rate, profit factor, etc. should match
   - Monitor live performance vs backtest

---

## Files Modified

1. **bot.py**
   - Added fixed TP/SL constants
   - Added calculate_fixed_tp_sl() method
   - Updated check_existing_positions()
   - Updated execute_trade_coin()
   - Cleaned up notifications

---

*Fix Applied: 2025-11-06*
*Status: ✅ COMPLETE*

