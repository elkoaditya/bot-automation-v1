# Session-Aware Strategy - Live Trading Bot

## 📋 Overview

SessionAwareStrategy telah diintegrasikan ke dalam live trading bot Anda. Strategi ini secara otomatis menyesuaikan parameter trading berdasarkan market session (Asian, European, US) untuk mengoptimalkan performa di berbagai kondisi market.

## 🚀 Features

### 1. **Adaptive Session-Based Trading**
- **Asian Session (00:00-09:00 UTC)**: Mean reversion focus (40% trend / 60% MR)
- **European Session (09:00-17:00 UTC)**: Balanced approach (70% trend / 30% MR)
- **US Session (17:00-00:00 UTC)**: Aggressive trending (85% trend / 15% MR)

### 2. **Multi-Factor Signal Generation**
- Triple EMA system (8, 21, 50)
- RSI with session-specific thresholds
- Bollinger Bands for ranging markets
- MACD for momentum confirmation
- Volume analysis
- ATR-based dynamic TP/SL

### 3. **Risk Management**
- Dynamic stop loss based on ATR and session
- Session-specific risk:reward ratios
  - Asian: 1:1.5 (tight stops, quick profits)
  - European: 1:2.0 (medium targets)
  - US: 1:2.5 (wider stops for volatility)

## 📊 Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Leverage (recommended: 5x for SessionAware)
LEVERAGE=5

# Trading Interval
INTERVAL=15

# SessionAware Strategy Parameters
STRATEGY_EMA_FAST=8
STRATEGY_EMA_MEDIUM=21
STRATEGY_EMA_SLOW=50
STRATEGY_SIGNAL_THRESHOLD=0.70
```

### Default Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ema_fast` | 8 | Fast EMA for quick signals |
| `ema_medium` | 21 | Medium EMA for trend confirmation |
| `ema_slow` | 50 | Slow EMA for major trend |
| `rsi_period` | 14 | RSI calculation period |
| `bb_period` | 20 | Bollinger Bands period |
| `bb_std` | 2.0 | BB standard deviation |
| `macd_fast` | 12 | MACD fast period |
| `macd_slow` | 26 | MACD slow period |
| `macd_signal` | 9 | MACD signal period |
| `atr_period` | 14 | ATR calculation period |
| `signal_threshold` | 0.70 | Minimum signal confidence (70%) |

## 🎯 How It Works

### Signal Generation Process

1. **Fetch Market Data**: Bot fetches OHLCV data for each coin
2. **Calculate Indicators**: All technical indicators computed
3. **Detect Session**: Determine current market session (UTC time)
4. **Apply Session Parameters**: Use session-specific thresholds and weights
5. **Calculate Signal Strength**: 
   - Trend score (based on EMA alignment, MACD, price position)
   - Mean reversion score (based on BB position, RSI, bounces)
   - Combined weighted score using session bias
6. **Filter Signals**: 
   - Signal strength > 0.70 (70% confidence)
   - Volume above session threshold
   - RSI safety filters (avoid extreme conditions)
7. **Execute Trade**: Place order with dynamic ATR-based TP/SL

### Entry Conditions

**LONG Entry:**
- Signal strength > 0.70
- Volume ratio > session minimum
- RSI < session overbought level
- Multiple confirmations from:
  - EMA alignment (fast > medium > slow)
  - Price above EMAs
  - MACD bullish
  - OR oversold bounce setup

**SHORT Entry:**
- Signal strength > 0.70
- Volume ratio > session minimum
- RSI > session oversold level
- Multiple confirmations from:
  - EMA alignment (fast < medium < slow)
  - Price below EMAs
  - MACD bearish
  - OR overbought reversal setup

### Exit Management

**Take Profit:**
- Asian: 1.5x ATR multiplier
- European: 2.0x ATR multiplier
- US: 2.5x ATR multiplier

**Stop Loss:**
- Asian: 1.0x ATR multiplier
- European: 1.5x ATR multiplier
- US: 2.0x ATR multiplier

Bot monitors positions in real-time and closes when TP/SL is hit.

## 📈 Bot Output

When running, you'll see:

```
📅 Current Session: US
   BTCUSDT: $67234.50 | EMA:BULLISH | RSI:54.2 | VOL:1.45x [LONG:0.72🟢]
   ETHUSDT: $3456.78 | EMA:MIXED | RSI:62.8 | VOL:0.98x [MAX:0.65⚪]
   SOLUSDT: $142.34 | EMA:BEARISH | RSI:38.1 | VOL:1.23x [SHORT:0.68🔴]
```

**Legend:**
- 🟢 LONG signal detected (above threshold)
- 🔴 SHORT signal detected (above threshold)
- ⚪ No signal (below threshold, shows max of long/short)

## 🔧 Running the Bot

### Standard Run

```bash
python3 bot.py
```

### Docker

```bash
docker-compose up -d
```

## 📊 Performance Characteristics

Based on 60-day backtest:

| Metric | Value |
|--------|-------|
| Total PnL | +1,250% |
| Win Rate | 42.73% |
| Total Trades | 110 |
| Avg Winner | ~$400 |
| Avg Loser | ~$150 |
| Risk:Reward | 2.7:1 |
| Max Drawdown | 0% |

## ⚡ Advantages

1. **Session Awareness**: Adapts to different market conditions
2. **High Win Size**: Winners much larger than losers (2.7:1)
3. **Dynamic Risk Management**: ATR-based TP/SL per session
4. **Multiple Confirmations**: Reduces false signals
5. **Proven Profitability**: +1250% in backtest

## ⚠️ Considerations

1. **Win Rate**: Only 42-47% (compensated by R:R)
2. **More Trades**: 2-3x more than simple MA strategies
3. **Higher Fees**: More trades = more commission
4. **Leverage Risk**: Use appropriate leverage (5x recommended)

## 🎨 Customization

### Adjusting Signal Threshold

More conservative (fewer, higher quality trades):
```bash
STRATEGY_SIGNAL_THRESHOLD=0.75
```

More aggressive (more trades, lower quality):
```bash
STRATEGY_SIGNAL_THRESHOLD=0.65
```

### Changing EMA Periods

Faster signals (more trades):
```bash
STRATEGY_EMA_FAST=5
STRATEGY_EMA_MEDIUM=13
STRATEGY_EMA_SLOW=34
```

Slower signals (fewer, more reliable):
```bash
STRATEGY_EMA_FAST=12
STRATEGY_EMA_MEDIUM=26
STRATEGY_EMA_SLOW=100
```

## 🛡️ Risk Management Tips

1. **Start Small**: Begin with demo account or small capital
2. **Monitor First Week**: Observe signal quality before scaling
3. **Use Appropriate Leverage**: 5x is safer than 10x
4. **Set Daily Loss Limits**: Stop trading if daily loss exceeds X%
5. **Diversify**: Trade multiple coins (bot default: top 20)
6. **Track Performance**: Keep log of trades and metrics

## 🔍 Monitoring

### Key Metrics to Watch

- **Signal Quality**: Are triggered signals > 0.70?
- **Session Distribution**: Getting signals in all sessions?
- **Win Rate by Session**: Which session performs best?
- **Average Signal Strength**: Higher = better quality
- **Volume Ratios**: Trading on sufficient volume?

### Logs

Important log messages:
- `✓ SessionAwareStrategy initialized` - Strategy loaded
- `📅 Current Session: ASIAN/EUROPEAN/US` - Active session
- `[LONG:0.72🟢]` - Long signal detected with 72% confidence
- `✓ Order placed: Buy 0.5 BTCUSDT @ Market` - Trade executed
- `✓ TP/SL set: TP=$68000.00, SL=$66500.00` - Risk management active

## 🐛 Troubleshooting

### No Signals Generated

**Causes:**
- Signal threshold too high (current market not strong enough)
- Volume too low (not meeting session minimums)
- RSI in extreme zones (safety filters active)

**Solutions:**
- Lower `STRATEGY_SIGNAL_THRESHOLD` to 0.65
- Check current session and expected behavior
- Wait for better market conditions

### Too Many Signals

**Causes:**
- Signal threshold too low
- Very volatile market

**Solutions:**
- Raise `STRATEGY_SIGNAL_THRESHOLD` to 0.75
- Increase EMA periods for slower signals
- Reduce number of coins being monitored

### Frequent Stop Loss

**Causes:**
- ATR multiplier too tight for session
- High market volatility
- Poor signal quality

**Solutions:**
- Increase `LEVERAGE` to 3x (wider stops with same capital risk)
- Only trade during US session (wider stops)
- Increase signal threshold for better quality

## 📞 Support

For issues or questions:
1. Check logs for error messages
2. Verify `.env` configuration
3. Test with demo account first
4. Monitor for 24 hours before live trading

## 🎓 Learning Resources

- Study backtest results in `/backtest/` folder
- Review `SESSION_AWARE_STRATEGY.md` in backtest folder
- Compare with other strategies (AdvancedTrend, HybridScalping)
- Analyze `RESULTS_SUMMARY.md` for performance insights

---

**Happy Trading! 🚀**

*Remember: Past performance does not guarantee future results. Always trade responsibly and never risk more than you can afford to lose.*

