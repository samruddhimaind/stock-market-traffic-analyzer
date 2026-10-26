import yfinance as yf
import pandas as pd
import numpy as np

def run_strategy_backtest(symbol: str, target_pct: float = 3.0, holding_days: int = 5):
    """
    Backtests a Volume Spike + RSI Reversal strategy on 6-month daily candle data.
    Returns Win Rate %, Total Signals, and Average Gain %.
    """
    if not symbol.endswith(".NS"):
        symbol = f"{symbol}.NS"

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="6mo")

        if df.empty or len(df) < 30:
            return {"status": "error", "message": "Insufficient historical data for backtesting."}

        # Calculate Technical Indicators
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        df['Avg_Volume'] = df['Volume'].rolling(window=20).mean()
        df['Vol_Ratio'] = df['Volume'] / df['Avg_Volume']

        df.dropna(inplace=True)

        trades = []
        for i in range(len(df) - holding_days):
            current_row = df.iloc[i]
            
            # Entry Signal Condition: Volume Spike > 1.2x AND RSI < 45 (Oversold/Dip)
            if current_row['Vol_Ratio'] >= 1.2 and current_row['RSI'] <= 45:
                entry_price = current_row['Close']
                future_prices = df['Close'].iloc[i+1 : i+1+holding_days]
                max_future_price = future_prices.max()

                max_gain_pct = ((max_future_price - entry_price) / entry_price) * 100
                is_win = max_gain_pct >= target_pct

                trades.append({
                    "date": df.index[i].strftime('%Y-%m-%d'),
                    "entry_price": round(entry_price, 2),
                    "max_gain_pct": round(max_gain_pct, 2),
                    "is_win": is_win
                })

        if not trades:
            return {
                "status": "success",
                "symbol": symbol.replace(".NS", ""),
                "total_signals": 0,
                "win_rate": 0.0,
                "avg_return": 0.0,
                "message": "No strategy entry signals triggered in past 6 months."
            }

        wins = sum(1 for t in trades if t["is_win"])
        win_rate = round((wins / len(trades)) * 100, 1)
        avg_return = round(sum(t["max_gain_pct"] for t in trades) / len(trades), 2)

        return {
            "status": "success",
            "symbol": symbol.replace(".NS", ""),
            "total_signals": len(trades),
            "win_rate": win_rate,
            "avg_return": avg_return,
            "target_pct": target_pct,
            "holding_days": holding_days
        }

    except Exception as e:
        print(f"Backtest error for {symbol}: {e}")
        return {"status": "error", "message": str(e)}