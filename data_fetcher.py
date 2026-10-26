import yfinance as yf
import pandas as pd
import requests
import time
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk

try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

sia = SentimentIntensityAnalyzer()

# Fast In-Memory Cache Dictionary
CACHE_STORE = {}
CACHE_TTL_SECONDS = 60  # Cache expires every 60 seconds

DEFAULT_SYMBOLS = [
    'RELIANCE.NS', 
    'TCS.NS', 
    'INFY.NS', 
    'HDFCBANK.NS', 
    'TATAMOTORS.NS',
    'ICICIBANK.NS',
    'SBIN.NS'
]

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(data, fast=12, slow=26, signal=9):
    exp1 = data.ewm(span=fast, adjust=False).mean()
    exp2 = data.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def calculate_vwap(hist_df):
    typical_price = (hist_df['High'] + hist_df['Low'] + hist_df['Close']) / 3
    vwap = (typical_price * hist_df['Volume']).cumsum() / hist_df['Volume'].cumsum()
    return vwap

def fetch_stock_news_sentiment(symbol_raw: str):
    """
    Fetches news headlines from Yahoo Finance and calculates Sentiment Score.
    """
    try:
        ticker = yf.Ticker(symbol_raw)
        news = ticker.news
        headlines = []
        
        if news:
            for item in news[:5]:
                title = ""
                if isinstance(item, dict):
                    title = item.get('title') or item.get('content', {}).get('title', '')
                elif hasattr(item, 'title'):
                    title = item.title

                if title:
                    headlines.append(title)
        
        if not headlines:
            return {"sentiment_score": 0.0, "label": "NEUTRAL ⚪", "top_news": "No recent headlines available"}
        
        scores = [sia.polarity_scores(text)['compound'] for text in headlines]
        avg_score = round(sum(scores) / len(scores), 2)
        
        if avg_score >= 0.05:
            label = "BULLISH 🟢"
        elif avg_score <= -0.05:
            label = "BEARISH 🔴"
        else:
            label = "NEUTRAL ⚪"

        return {
            "sentiment_score": avg_score,
            "label": label,
            "top_news": headlines[0]
        }
    except Exception as e:
        print(f"Sentiment analysis error for {symbol_raw}: {e}")
        return {"sentiment_score": 0.0, "label": "NEUTRAL ⚪", "top_news": "N/A"}

def fetch_stock_summary(symbol: str):
    symbol = symbol.strip().upper()
    if not symbol.endswith(".NS"):
        symbol = f"{symbol}.NS"

    current_time = time.time()
    
    if symbol in CACHE_STORE:
        cached_item = CACHE_STORE[symbol]
        if current_time - cached_item['timestamp'] < CACHE_TTL_SECONDS:
            return cached_item['data']

    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="3mo")
    
    if hist.empty:
        return None
    
    hist['RSI'] = calculate_rsi(hist['Close'])
    hist['MACD'], hist['MACD_Signal'] = calculate_macd(hist['Close'])
    hist['VWAP'] = calculate_vwap(hist)
    
    latest_data = hist.iloc[-1]
    avg_volume = hist['Volume'].iloc[:-1].mean()
    
    current_price = round(latest_data['Close'], 2)
    today_volume = int(latest_data['Volume'])
    volume_ratio = round(today_volume / avg_volume, 2) if avg_volume > 0 else 1.0
    
    rsi_val = round(latest_data['RSI'], 2) if pd.notnull(latest_data['RSI']) else 50.0
    macd_val = round(latest_data['MACD'], 2) if pd.notnull(latest_data['MACD']) else 0.0
    macd_signal_val = round(latest_data['MACD_Signal'], 2) if pd.notnull(latest_data['MACD_Signal']) else 0.0
    vwap_val = round(latest_data['VWAP'], 2) if pd.notnull(latest_data['VWAP']) else current_price
    
    macd_signal_text = "BULLISH CROSS" if macd_val > macd_signal_val else "BEARISH CROSS"
    vwap_signal_text = "ABOVE VWAP (Strong)" if current_price >= vwap_val else "BELOW VWAP (Weak)"

    sentiment_data = fetch_stock_news_sentiment(symbol)

    result = {
        "symbol": symbol.replace(".NS", "").upper(),
        "price": current_price,
        "volume": today_volume,
        "avg_volume_10d": int(avg_volume),
        "traffic_spike_ratio": volume_ratio,
        "rsi": rsi_val,
        "macd": macd_val,
        "macd_signal": macd_signal_val,
        "macd_trend": macd_signal_text,
        "vwap": vwap_val,
        "vwap_trend": vwap_signal_text,
        "sentiment_score": sentiment_data["sentiment_score"],
        "sentiment_label": sentiment_data["label"],
        "top_headline": sentiment_data["top_news"],
        "day_high": round(latest_data['High'], 2),
        "day_low": round(latest_data['Low'], 2)
    }

    CACHE_STORE[symbol] = {
        "timestamp": current_time,
        "data": result
    }

    return result

def get_high_traffic_stocks(symbols=DEFAULT_SYMBOLS):
    stock_data_list = []
    for symbol in symbols:
        try:
            data = fetch_stock_summary(symbol)
            if data:
                stock_data_list.append(data)
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            
    return sorted(stock_data_list, key=lambda x: x['traffic_spike_ratio'], reverse=True)

# Major NSE Sector Indices Tickers on Yahoo Finance
SECTOR_MAP = {
    "NIFTY BANK": "^NSEBANK",
    "NIFTY IT": "^CNXIT",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY FMCG": "^CNXFMCG",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY ENERGY": "^CNXENERGY"
}

def fetch_sector_heatmaps():
    """
    Fetches real-time percentage performance for top NSE Sectoral Indices.
    """
    sector_results = []
    
    for sector_name, ticker_symbol in SECTOR_MAP.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="5d")
            
            if not hist.empty and len(hist) >= 2:
                latest_close = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2]
                pct_change = round(((latest_close - prev_close) / prev_close) * 100, 2)
            else:
                pct_change = 0.0

            sector_results.append({
                "sector": sector_name,
                "change_pct": pct_change,
                "status": "BULLISH" if pct_change >= 0 else "BEARISH"
            })
        except Exception as e:
            print(f"Error fetching sector {sector_name}: {e}")
            sector_results.append({
                "sector": sector_name,
                "change_pct": 0.0,
                "status": "NEUTRAL"
            })
            
    return sector_results

def fetch_stock_chart_data(symbol: str, period="3mo"):
    """
    Updated chart fetcher to support multi-timeframe periods: 1mo, 3mo, 6mo, 1y.
    """
    if not symbol.endswith(".NS"):
        symbol = f"{symbol}.NS"
        
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period)
    
    candles = []
    for index, row in hist.iterrows():
        candles.append({
            "time": index.strftime('%Y-%m-%d'),
            "open": round(row['Open'], 2),
            "high": round(row['High'], 2),
            "low": round(row['Low'], 2),
            "close": round(row['Close'], 2),
            "volume": int(row['Volume'])
        })
    return candles