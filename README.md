# Bybit Trading Bot with Telegram Notifications

Bot trading otomatis dengan leverage menggunakan Bybit API demo untuk trading dan real market data untuk candlestick, dengan strategi Moving Average dan notifikasi Telegram termasuk grafik detail.

## Fitur

- Trading dengan leverage (configurable via env)
- Strategi Moving Average crossover
- Demo mode menggunakan Bybit demo API (`https://api-demo.bybit.com`)
- Real market data untuk candlestick (bukan testnet)
- Notifikasi Telegram dengan chart visualisasi posisi entry, TP, dan SL
- Take Profit: +1% dari entry price
- Stop Loss: -1% dari entry price

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

- `BYBIT_API_KEY` - API key untuk Bybit
- `BYBIT_API_SECRET` - API secret untuk Bybit
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `TELEGRAM_CHAT_ID` - Chat ID untuk notifications
- `LEVERAGE` - Leverage multiplier (default: 10)
- `TRADING_PAIR` - Trading pair (default: BTCUSDT)
- `ENVIRONMENT` - demo atau production (default: demo)
- `INTERVAL` - Candlestick interval dalam menit (default: 15)

## Struktur Project

```
.
├── bot.py                 # Main bot script
├── config.py              # Configuration loader
├── strategies/
│   └── ma_strategy.py     # MA strategy implementation
├── exchanges/
│   └── bybit_client.py    # Bybit API wrapper
├── notifications/
│   └── telegram_bot.py    # Telegram handler
├── utils/
│   └── chart_generator.py # Chart generator
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Strategi Trading

Bot menggunakan Moving Average crossover strategy:
- Fast MA: 20 periods
- Slow MA: 50 periods
- Entry: Fast MA crosses above Slow MA (bullish)
- Exit: TP (+1%) atau SL (-1%) hit

## Disclaimer

Bot ini untuk tujuan edukasi dan testing. Gunakan dengan risiko sendiri. Pastikan untuk test dengan demo account terlebih dahulu.

