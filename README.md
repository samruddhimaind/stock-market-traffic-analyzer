# 📊 Institutional Stock Market Traffic & Technical Screener

An end-to-end full-stack stock market analytics dashboard and technical screener built with **Python, FastAPI, Tailwind CSS, and TradingView Lightweight Charts**. 

This application identifies real-time volume spikes (traffic ratio), calculates core technical indicators (RSI, MACD, VWAP), performs AI news sentiment analysis, and sends real-time alerts via Telegram.

---

## 🔥 Key Features

- **Volume Spike & Traffic Detection**: Calculates daily volume vs. 10-day moving average to spot unusual trading traffic ($>1.0x$).
- **Advanced Technical Matrix**:
  - **RSI (14)**: Relative Strength Index to identify Overbought/Oversold levels.
  - **MACD**: Moving Average Convergence Divergence for Bullish/Bearish crossover trends.
  - **VWAP**: Volume Weighted Average Price benchmark for intraday trend strength.
- **AI Financial News Sentiment Analysis**: Uses NLTK VADER engine to analyze live Yahoo Finance news headlines into Bullish 🟢 / Bearish 🔴 / Neutral ⚪ signals.
- **Interactive Candlestick Charts**: Embedded TradingView Lightweight Charts for smooth OHLC visualization.
- **Custom Stock Search**: Ticker search bar for any NSE stock (e.g., `WIPRO`, `TATAPOWER`, `ZOMATO`).
- **High Performance Caching**: 60-second in-memory caching mechanism reducing API response times to $<50\text{ms}$.
- **Telegram Bot Alert Integration**: Real-time push notifications sent directly to Telegram whenever a high-traffic volume spike occurs.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.x, FastAPI, Uvicorn
- **Data Engine & Analysis**: Pandas, YFinance, NLTK (VADER Sentiment)
- **Frontend**: HTML5, Tailwind CSS, TradingView Lightweight Charts JS
- **Notifications**: Telegram Bot Webhook API

---

## 🚀 How to Run Locally

### 1. Clone Repository & Setup Virtual Environment
```bash
git clone [https://github.com/samruddhimaind/stock-market-traffic-analyzer.git](https://github.com/samruddhimaind/stock-market-traffic-analyzer.git)
cd stock-market-traffic-analyzer

python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate