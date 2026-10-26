import os
from google import genai
from google.genai import types

# Set your Gemini API key environment variable or pass directly
# e.g., os.environ["GEMINI_API_KEY"] = "YOUR_GEMINI_API_KEY"

def generate_ai_trade_summary(stock_data: dict) -> str:
    """
    Generates a professional 2-3 line AI trade insight using Gemini based on technical and sentiment metrics.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # Fallback dynamic summary generator if Gemini API key is not configured
        return (
            f"Automated Insight for {stock_data.get('symbol')}: "
            f"Trading at ₹{stock_data.get('price')} with a {stock_data.get('traffic_spike_ratio')}x volume surge. "
            f"RSI stands at {stock_data.get('rsi')} with a {stock_data.get('macd_trend')} trend. "
            f"Overall market sentiment is {stock_data.get('sentiment_label')}."
        )

    try:
        client = genai.Client(api_key=api_key)
        
        prompt = (
            f"Analyze the following stock metrics and write a concise 2-sentence executive summary and trade insight for an investor:\n"
            f"- Ticker: {stock_data.get('symbol')}\n"
            f"- Price: ₹{stock_data.get('price')}\n"
            f"- Intraday Volume Spike: {stock_data.get('traffic_spike_ratio')}x average volume\n"
            f"- RSI (14): {stock_data.get('rsi')}\n"
            f"- MACD Trend: {stock_data.get('macd_trend')}\n"
            f"- VWAP Trend: {stock_data.get('vwap_trend')}\n"
            f"- News Sentiment: {stock_data.get('sentiment_label')} (Score: {stock_data.get('sentiment_score')})\n"
            f"- Top Headline: {stock_data.get('top_headline')}\n\n"
            f"Provide a clear, objective analysis in 2 professional English sentences without disclaimers."
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=150
            )
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini AI Insight Generation Error: {e}")
        return (
            f"{stock_data.get('symbol')} displays a {stock_data.get('traffic_spike_ratio')}x volume surge with "
            f"{stock_data.get('sentiment_label')} sentiment and a {stock_data.get('macd_trend')} technical structure."
        )