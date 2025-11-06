# ⚠️ CRITICAL ISSUE: TP/SL Implementation Mismatch

## Problem Summary

**Backtest dan Bot TIDAK menggunakan TP/SL yang sama!**

---

## Detailed Analysis

### 1. BACKTEST IMPLEMENTATION

#### A. SessionAware Strategy MENGHITUNG Dynamic TP/SL
```python
# backtest/strategies/session_aware_strategy.py (lines 361-380)

for session_name in ['asian', 'european', 'us']:
    session_params = self.calculate_session_parameters(session_name)
    atr_mult = session_params['atr_multiplier']
    
    if session_name == 'asian':
        df.loc[session_mask, 'suggested_stop_pct'] = df['atr_pct'] * atr_mult      # ATR × 1.0
        df.loc[session_mask, 'suggested_tp_pct'] = df['atr_pct'] * (atr_mult * 1.5)  # ATR × 1.5
    elif session_name == 'european':
        df.loc[session_mask, 'suggested_stop_pct'] = df['atr_pct'] * atr_mult      # ATR × 1.5
        df.loc[session_mask, 'suggested_tp_pct'] = df['atr_pct'] * (atr_mult * 2.0)  # ATR × 3.0
    else:  # US
        df.loc[session_mask, 'suggested_stop_pct'] = df['atr_pct'] * atr_mult      # ATR × 2.0
        df.loc[session_mask, 'suggested_tp_pct'] = df['atr_pct'] * (atr_mult * 2.5)  # ATR × 5.0
```

**✅ Strategy menghasilkan dynamic TP/SL per session**

#### B. Backtest Engine TIDAK MENGGUNAKAN Dynamic TP/SL
```python
# backtest/backtest/engine.py (lines 34-44)

if stop_loss_pct is None:
    stop_loss_pct = config.DEFAULT_STOP_LOSS  # ❌ Fixed 2.5%
if take_profit_pct is None:
    take_profit_pct = config.DEFAULT_TAKE_PROFIT  # ❌ Fixed 5.0%

self.stop_loss_pct = stop_loss_pct
self.take_profit_pct = take_profit_pct
```

```python
# backtest/backtest/engine.py (lines 91-92)

# For LONG positions
stop_price = trade.entry_price * (1 - self.stop_loss_pct)  # ❌ Uses fixed 2.5%
tp_price = trade.entry_price * (1 + self.take_profit_pct)  # ❌ Uses fixed 5.0%
```

**❌ Engine menggunakan FIXED TP/SL dari config, MENGABAIKAN dynamic values dari strategy!**

#### C. Config Values
```python
# backtest/config.py (lines 16-17)

DEFAULT_STOP_LOSS = 0.025   # Fixed 2.5% for ALL sessions
DEFAULT_TAKE_PROFIT = 0.05  # Fixed 5.0% for ALL sessions
```

---

### 2. BOT IMPLEMENTATION

```python
# bot.py (lines 399-404)

# Calculate TP/SL using ATR and session data from signal
atr_pct = signal_data.get('atr_pct')
session = signal_data.get('session')
tp_sl = self.strategy.calculate_tp_sl(
    entry_price, side, atr_pct=atr_pct, session=session
)
```

```python
# strategies/session_aware_strategy.py (lines 440-451)

# Calculate dynamic TP/SL based on ATR if provided
if atr_pct is not None and tp_percent is None and sl_percent is None:
    sl_pct = atr_pct * atr_multiplier * 100  # Session-specific multiplier
    
    if session == 'asian':
        tp_pct = sl_pct * 1.5   # ✅ 1:1.5 R:R
    elif session == 'european':
        tp_pct = sl_pct * 2.0   # ✅ 1:2.0 R:R
    else:  # US
        tp_pct = sl_pct * 2.5   # ✅ 1:2.5 R:R
```

**✅ Bot menggunakan dynamic TP/SL per session dengan ATR multipliers**

---

## Comparison Table

| Aspect | Backtest | Bot | Match? |
|--------|----------|-----|--------|
| **Asian Session SL** | **2.5% (fixed)** | **ATR × 1.0 (dynamic)** | ❌ NO |
| **Asian Session TP** | **5.0% (fixed)** | **SL × 1.5 (dynamic)** | ❌ NO |
| **European Session SL** | **2.5% (fixed)** | **ATR × 1.5 (dynamic)** | ❌ NO |
| **European Session TP** | **5.0% (fixed)** | **SL × 2.0 (dynamic)** | ❌ NO |
| **US Session SL** | **2.5% (fixed)** | **ATR × 2.0 (dynamic)** | ❌ NO |
| **US Session TP** | **5.0% (fixed)** | **SL × 2.5 (dynamic)** | ❌ NO |
| **Session Awareness** | ❌ No | ✅ Yes | ❌ NO |
| **ATR-based** | ❌ No | ✅ Yes | ❌ NO |
| **Volatility Adaptive** | ❌ No | ✅ Yes | ❌ NO |

---

## Example Scenario

### Scenario: BTCUSDT @ $50,000, ATR = $500 (1% of price)

#### Asian Session (Low Volatility)
| | Backtest | Bot |
|---|----------|-----|
| **Stop Loss** | $48,750 (2.5% fixed) | $49,500 (ATR × 1.0 = 1%) |
| **Take Profit** | $52,500 (5.0% fixed) | $49,750 (SL × 1.5 = 1.5%) |
| **Risk:Reward** | 1:2.0 | 1:1.5 |

#### European Session (Medium Volatility)
| | Backtest | Bot |
|---|----------|-----|
| **Stop Loss** | $48,750 (2.5% fixed) | $49,250 (ATR × 1.5 = 1.5%) |
| **Take Profit** | $52,500 (5.0% fixed) | $51,500 (SL × 2.0 = 3%) |
| **Risk:Reward** | 1:2.0 | 1:2.0 |

#### US Session (High Volatility)
| | Backtest | Bot |
|---|----------|-----|
| **Stop Loss** | $48,750 (2.5% fixed) | $49,000 (ATR × 2.0 = 2%) |
| **Take Profit** | $52,500 (5.0% fixed) | $52,500 (SL × 2.5 = 5%) |
| **Risk:Reward** | 1:2.0 | 1:2.5 |

---

## Impact Analysis

### ❌ Current Problems

1. **Backtest Results NOT Representative**
   - Backtest menggunakan fixed TP/SL yang tidak reflect session behavior
   - Bot menggunakan adaptive TP/SL berdasarkan volatility

2. **Tighter Stops in Bot**
   - Bot akan exit lebih cepat saat volatility rendah (Asian)
   - Bot akan hold longer saat volatility tinggi (US)

3. **Different Risk:Reward Ratios**
   - Backtest: Fixed 1:2.0 untuk semua session
   - Bot: Adaptive 1:1.5 (Asian), 1:2.0 (EU), 1:2.5 (US)

4. **Strategy Benefits Lost**
   - SessionAware strategy DESIGNED untuk adaptive TP/SL
   - Backtest NOT using this key feature!

---

## Root Cause

**Backtest Engine mengabaikan `suggested_stop_pct` dan `suggested_tp_pct` dari strategy!**

```python
# Strategy CALCULATES these values:
df['suggested_stop_pct'] = ...  # Dynamic per session
df['suggested_tp_pct'] = ...     # Dynamic per session

# But Engine IGNORES them and uses:
self.stop_loss_pct = config.DEFAULT_STOP_LOSS      # Fixed 2.5%
self.take_profit_pct = config.DEFAULT_TAKE_PROFIT  # Fixed 5.0%
```

---

## Solution Required

### Option 1: Fix Backtest Engine (RECOMMENDED)

Modify `BacktestEngine` to use dynamic TP/SL from strategy signals:

```python
# In engine.py, when processing signals:
if hasattr(signal, 'suggested_stop_pct'):
    stop_loss_pct = signal.suggested_stop_pct
    take_profit_pct = signal.suggested_tp_pct
else:
    stop_loss_pct = self.stop_loss_pct
    take_profit_pct = self.take_profit_pct

# Then use these dynamic values:
stop_price = trade.entry_price * (1 - stop_loss_pct)
tp_price = trade.entry_price * (1 + take_profit_pct)
```

### Option 2: Update Strategy to Return TP/SL with Signals

Modify strategy to return TP/SL values alongside signals.

---

## Recommendation

**URGENT: Fix backtest engine to use dynamic TP/SL!**

Without this fix:
- ✅ Signal logic is aligned
- ❌ But TP/SL execution is completely different
- ❌ Backtest results will NOT match bot performance
- ❌ Strategy's session-aware TP/SL design is wasted

---

*Analysis Date: 2025-11-06*

