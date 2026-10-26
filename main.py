from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import data_fetcher

app = FastAPI(title="Stock Traffic Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/stocks/high-traffic")
def get_high_traffic_stocks():
    stocks = data_fetcher.get_high_traffic_stocks()
    return {"status": "success", "count": len(stocks), "data": stocks}

@app.get("/api/stocks/search")
def search_stock(symbol: str = Query(...)):
    """
    Search any NSE stock by symbol (e.g. TATAPOWER, WIPRO, ZOMATO)
    """
    data = data_fetcher.fetch_stock_summary(symbol)
    if data:
        return {"status": "success", "data": data}
    return {"status": "error", "message": f"Stock '{symbol}' not found or invalid."}

@app.get("/api/stocks/chart")
def get_stock_chart(symbol: str = Query(...)):
    chart_data = data_fetcher.fetch_stock_chart_data(symbol)
    return {"status": "success", "symbol": symbol, "data": chart_data}