from fastapi import FastAPI, Query, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import timedelta

import data_fetcher
import database
import models
import auth_utils
import ai_engine
import backtester

# Create Database Tables Automatically
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Stock Market Traffic Analyzer API with Auth")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# PYDANTIC SCHEMAS (Request/Response Models)
# ==========================================
class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str

class WatchlistAdd(BaseModel):
    symbol: str

# ==========================================
# AUTHENTICATION ENDPOINTS
# ==========================================
@app.post("/api/auth/register", response_model=Token)
def register(user_data: UserRegister, db: Session = Depends(database.get_db)):
    # Check if username or email already exists
    existing_user = db.query(models.User).filter(
        (models.User.username == user_data.username) | (models.User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered."
        )

    # Hash password and store user
    hashed_pwd = auth_utils.hash_password(user_data.password)
    new_user = models.User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_pwd
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate JWT Token
    access_token = auth_utils.create_access_token(data={"sub": new_user.username})
    return {"access_token": access_token, "token_type": "bearer", "username": new_user.username}

@app.post("/api/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    if not user or not auth_utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_utils.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer", "username": user.username}

# ==========================================
# USER WATCHLIST ENDPOINTS (Protected)
# ==========================================
@app.post("/api/user/watchlist/add")
def add_to_watchlist(
    item: WatchlistAdd,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(database.get_db)
):
    symbol_clean = item.symbol.strip().upper()
    
    # Check if stock already in watchlist
    existing = db.query(models.Watchlist).filter(
        models.Watchlist.user_id == current_user.id,
        models.Watchlist.symbol == symbol_clean
    ).first()
    
    if existing:
        return {"status": "info", "message": f"{symbol_clean} is already in your watchlist."}

    new_entry = models.Watchlist(symbol=symbol_clean, user_id=current_user.id)
    db.add(new_entry)
    db.commit()
    
    return {"status": "success", "message": f"{symbol_clean} added to your watchlist!"}

@app.get("/api/user/watchlist")
def get_user_watchlist(
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(database.get_db)
):
    watchlist_entries = db.query(models.Watchlist).filter(models.Watchlist.user_id == current_user.id).all()
    symbols = [w.symbol for w in watchlist_entries]
    
    if not symbols:
        return {"status": "success", "count": 0, "data": []}

    # Fetch live analysis for saved watchlist stocks
    stocks_data = []
    for sym in symbols:
        data = data_fetcher.fetch_stock_summary(sym)
        if data:
            stocks_data.append(data)

    return {"status": "success", "count": len(stocks_data), "data": stocks_data}

@app.delete("/api/user/watchlist/remove")
def remove_from_watchlist(
    symbol: str = Query(...),
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(database.get_db)
):
    symbol_clean = symbol.strip().upper()
    entry = db.query(models.Watchlist).filter(
        models.Watchlist.user_id == current_user.id,
        models.Watchlist.symbol == symbol_clean
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Stock not found in your watchlist.")

    db.delete(entry)
    db.commit()
    return {"status": "success", "message": f"{symbol_clean} removed from your watchlist."}

# ==========================================
# PUBLIC STOCK MARKET ENDPOINTS
# ==========================================
@app.get("/")
def home():
    return {"message": "Stock Market Traffic Analyzer API is Live with DB & Auth!"}

@app.get("/api/stocks/high-traffic")
def get_high_traffic_stocks():
    stocks = data_fetcher.get_high_traffic_stocks()
    return {"status": "success", "count": len(stocks), "data": stocks}

@app.get("/api/stocks/search")
def search_stock(symbol: str = Query(...)):
    symbol_clean = symbol.strip().upper()
    data = data_fetcher.fetch_stock_summary(symbol_clean)
    if data:
        return {"status": "success", "data": data}
    return {"status": "error", "message": f"Stock '{symbol}' not found or invalid."}

@app.get("/api/stocks/chart")
def get_stock_chart(symbol: str = Query(...)):
    chart_data = data_fetcher.fetch_stock_chart_data(symbol)
    return {"status": "success", "symbol": symbol, "data": chart_data}

@app.get("/api/stocks/ai-insight")
def get_ai_stock_insight(symbol: str = Query(...)):
    """
    Generates AI-powered trade summary for any given stock ticker.
    """
    symbol_clean = symbol.strip().upper()
    summary_data = data_fetcher.fetch_stock_summary(symbol_clean)
    
    if not summary_data:
        raise HTTPException(status_code=404, detail="Stock symbol not found or data unavailable.")
    
    insight_text = ai_engine.generate_ai_trade_summary(summary_data)
    
    return {
        "status": "success",
        "symbol": summary_data["symbol"],
        "ai_insight": insight_text
    }

@app.get("/api/sectors/heatmap")
def get_sector_heatmaps():
    """
    Returns real-time percentage change performance for major NSE Sectoral Indices.
    """
    try:
        sectors_data = data_fetcher.fetch_sector_heatmaps()
        return {"status": "success", "data": sectors_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/chart")
def get_stock_chart(symbol: str = Query(...), period: str = Query("3mo")):
    """
    Returns candlestick chart data with period selector (1mo, 3mo, 6mo, 1y).
    """
    chart_data = data_fetcher.fetch_stock_chart_data(symbol, period=period)
    return {"status": "success", "symbol": symbol, "period": period, "data": chart_data}

class AlertRuleCreate(BaseModel):
    symbol: str
    min_volume_ratio: Optional[float] = 1.5
    min_rsi: Optional[float] = 30.0
    max_rsi: Optional[float] = 70.0

@app.post("/api/user/alerts/add")
def create_alert_rule(
    rule: AlertRuleCreate,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(database.get_db)
):
    symbol_clean = rule.symbol.strip().upper()
    new_rule = models.AlertRule(
        symbol=symbol_clean,
        min_volume_ratio=rule.min_volume_ratio,
        min_rsi=rule.min_rsi,
        max_rsi=rule.max_rsi,
        user_id=current_user.id
    )
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    return {"status": "success", "message": f"Alert rule created for {symbol_clean}!"}

@app.get("/api/user/alerts/check")
def check_active_alerts(
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(database.get_db)
):
    user_rules = db.query(models.AlertRule).filter(
        models.AlertRule.user_id == current_user.id,
        models.AlertRule.is_active == True
    ).all()
    
    triggered_alerts = []
    for rule in user_rules:
        data = data_fetcher.fetch_stock_summary(rule.symbol)
        if data:
            if (data["traffic_spike_ratio"] >= rule.min_volume_ratio and 
                (data["rsi"] <= rule.min_rsi or data["rsi"] >= rule.max_rsi)):
                triggered_alerts.append({
                    "symbol": rule.symbol,
                    "price": data["price"],
                    "volume_ratio": data["traffic_spike_ratio"],
                    "rsi": data["rsi"],
                    "message": f"Volume spike {data['traffic_spike_ratio']}x with RSI at {data['rsi']}!"
                })
                
    return {"status": "success", "triggered_count": len(triggered_alerts), "alerts": triggered_alerts}

@app.get("/api/stocks/backtest")
def get_strategy_backtest(symbol: str = Query(...)):
    """
    Returns 6-month historical strategy backtest metrics (Win Rate, Total Signals, Avg Gain).
    """
    symbol_clean = symbol.strip().upper()
    result = backtester.run_strategy_backtest(symbol_clean)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Backtest failed."))
    return result

@app.get("/api/user/alerts/test-trigger")
def test_alert_trigger():
    """
    Mock endpoint to force trigger a notification alert & sound for testing UI.
    """
    return {
        "status": "success",
        "triggered_count": 1,
        "alerts": [
            {
                "symbol": "TEST_STOCK",
                "price": 450.50,
                "volume_ratio": 2.8,
                "rsi": 25.4,
                "message": "TEST ALERT: Volume spike 2.8x with RSI at 25.4 (Oversold Signal)!"
            }
        ]
    }

class WatchlistRemove(BaseModel):
    symbol: str

@app.delete("/api/user/watchlist/remove")
def remove_from_watchlist(
    symbol: str = Query(...),
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(database.get_db)
):
    symbol_clean = symbol.strip().upper()
    watchlist_entry = db.query(models.Watchlist).filter(
        models.Watchlist.user_id == current_user.id,
        models.Watchlist.symbol == symbol_clean
    ).first()

    if not watchlist_entry:
        raise HTTPException(status_code=404, detail="Stock not found in your watchlist.")

    db.delete(watchlist_entry)
    db.commit()

    return {"status": "success", "message": f"{symbol_clean} removed from Watchlist!"}

class PaymentOrderRequest(BaseModel):
    amount: float = 499.0  # PRO Subscription Price in INR

class PaymentVerifyRequest(BaseModel):
    order_id: str
    payment_id: str

@app.post("/api/payment/create-order")
def create_payment_order(
    req: PaymentOrderRequest,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Creates a transaction order ID for PRO upgrade.
    """
    import uuid
    dummy_order_id = f"order_{uuid.uuid4().hex[:12]}"
    
    new_tx = models.PaymentTransaction(
        order_id=dummy_order_id,
        amount=req.amount,
        status="CREATED",
        user_id=current_user.id
    )
    db.add(new_tx)
    db.commit()

    return {
        "status": "success",
        "order_id": dummy_order_id,
        "amount": req.amount,
        "currency": "INR",
        "key": "rzp_test_dummy_key"  # Place your actual Razorpay Key ID here
    }

@app.post("/api/payment/verify")
def verify_payment(
    req: PaymentVerifyRequest,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Verifies payment completion and grants 30-day PRO subscription access to user.
    """
    tx = db.query(models.PaymentTransaction).filter(
        models.PaymentTransaction.order_id == req.order_id,
        models.PaymentTransaction.user_id == current_user.id
    ).first()

    if not tx:
        raise HTTPException(status_code=404, detail="Payment Order not found.")

    tx.payment_id = req.payment_id
    tx.status = "SUCCESS"

    # Grant 30 Days PRO Access
    current_user.is_pro = True
    current_user.pro_expires_at = datetime.utcnow() + timedelta(days=30)

    db.commit()

    return {
        "status": "success",
        "message": "🎉 Payment Successful! Your PRO Subscription is active for 30 days.",
        "is_pro": True
    }

@app.get("/api/user/status")
def get_user_status(current_user: models.User = Depends(auth_utils.get_current_user)):
    return {
        "username": current_user.username,
        "is_pro": current_user.is_pro,
        "pro_expires_at": current_user.pro_expires_at.strftime("%Y-%m-%d") if current_user.pro_expires_at else None
    }