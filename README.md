# Bybit Trading Bot with Telegram Notifications

Bot trading otomatis dengan leverage menggunakan Bybit API demo untuk trading dan real market data untuk candlestick, dengan **Session-Aware Multi-Strategy** dan notifikasi Telegram termasuk grafik detail.

## Fitur

- ⚡ Trading dengan leverage (default: 5x, configurable)
- 🌍 **Session-Aware Strategy** - Adaptif berdasarkan market session (Asian/European/US)
- 📊 Multi-indicator signals (EMA, RSI, MACD, Bollinger Bands, ATR, Volume)
- 🎯 Dynamic TP/SL based on ATR and market session
- 🤖 Demo mode menggunakan Bybit demo API (`https://api-demo.bybit.com`)
- 📈 Real market data untuk candlestick (bukan testnet)
- 💬 Notifikasi Telegram dengan chart visualisasi posisi entry, TP, dan SL
- 🔄 Multi-coin trading (top 20 trending coins by volume)
- 🛡️ Session-specific risk management (R:R ratio 1.5:1 to 2.5:1)

## Setup

### 1. Clone repository dan setup environment

```bash
cp .env.example .env
```

Edit `.env` file dan isi dengan:
- Bybit API Key dan Secret
- Telegram Bot Token dan Chat ID
- Konfigurasi trading (leverage, pair, dll)

### 2. Build dan jalankan dengan Docker

```bash
docker-compose up --build
```

Atau jalankan langsung:

```bash
docker build -t trading-bot .
docker run --env-file .env trading-bot
```

### 3. Monitor trading activities

Bot akan mengirim notifikasi ke Telegram setiap ada aktivitas trading termasuk:
- Entry signal dengan chart
- Exit signal (TP/SL hit) dengan chart
- Error notifications

## Konfigurasi

### Environment Variables

**Required:**
- `BYBIT_API_KEY` - API key untuk Bybit
- `BYBIT_API_SECRET` - API secret untuk Bybit
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `TELEGRAM_CHAT_ID` - Chat ID untuk notifications

**Trading Configuration:**
- `LEVERAGE` - Leverage multiplier (default: 5, recommended for SessionAware)
- `TRADING_PAIR` - Fallback trading pair (default: BTCUSDT)
- `ENVIRONMENT` - demo atau production (default: demo)
- `INTERVAL` - Candlestick interval dalam menit (default: 15)

**SessionAware Strategy Parameters:**
- `STRATEGY_EMA_FAST` - Fast EMA period (default: 8)
- `STRATEGY_EMA_MEDIUM` - Medium EMA period (default: 21)
- `STRATEGY_EMA_SLOW` - Slow EMA period (default: 50)
- `STRATEGY_SIGNAL_THRESHOLD` - Minimum signal confidence 0-1 (default: 0.70)

## Struktur Project

```
.
├── bot.py                          # Main bot script
├── config.py                       # Configuration loader
├── strategies/
│   ├── ma_strategy.py              # MA strategy (legacy)
│   └── session_aware_strategy.py   # SessionAware strategy (active)
├── exchanges/
│   └── bybit_client.py             # Bybit API wrapper
├── notifications/
│   └── telegram_bot.py             # Telegram handler
├── utils/
│   └── chart_generator.py          # Chart generator
├── backtest/                       # Backtesting system & results
│   ├── strategies/
│   │   └── session_aware_strategy.py
│   ├── RESULTS_SUMMARY.md
│   └── SESSION_AWARE_STRATEGY.md
├── SESSION_AWARE_STRATEGY.md       # Strategy documentation
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Strategi Trading

Bot menggunakan **Session-Aware Multi-Strategy** yang adaptif:

### Market Sessions
- **Asian Session (00:00-09:00 UTC)**: Focus pada mean reversion, ranging markets
- **European Session (09:00-17:00 UTC)**: Balanced trend following dengan filter ketat
- **US Session (17:00-00:00 UTC)**: Aggressive trend following, high volatility

### Technical Indicators
- **Triple EMA System** (8, 21, 50) - Trend direction
- **RSI** (14) with session-specific thresholds - Momentum
- **Bollinger Bands** (20, 2.0) - Volatility & ranging
- **MACD** (12, 26, 9) - Momentum confirmation
- **ATR** (14) - Dynamic TP/SL calculation
- **Volume Analysis** - Session-specific volume filters

### Entry Rules
- Signal strength > 70% confidence
- Multiple indicator confirmations
- Volume above session threshold
- RSI safety filters

### Exit Rules
- **Dynamic TP/SL** based on ATR and session:
  - Asian: SL = 1.0×ATR, TP = 1.5×ATR (R:R 1:1.5)
  - European: SL = 1.5×ATR, TP = 3.0×ATR (R:R 1:2.0)
  - US: SL = 2.0×ATR, TP = 5.0×ATR (R:R 1:2.5)

### Backtest Performance (60 days)
- **Total PnL**: +1,250%
- **Win Rate**: 42.73%
- **Total Trades**: 110
- **Risk:Reward**: 2.7:1
- **Max Drawdown**: 0%

📖 **Untuk detail lengkap**, baca [SESSION_AWARE_STRATEGY.md](SESSION_AWARE_STRATEGY.md)

## Disclaimer

Bot ini untuk tujuan edukasi dan testing. Gunakan dengan risiko sendiri. Pastikan untuk test dengan demo account terlebih dahulu.

