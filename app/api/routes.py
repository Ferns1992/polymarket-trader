from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, List
from app.database import get_db
from app.config import settings
from app.models.models import (
    User,
    Position,
    Trade,
    AISettings,
    BotSettings,
    TradeSide,
    TradeStatus,
)
from app.services.ai_service import AIService, BotService
from app.services.polymarket_service import PolymarketService
import json

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

router = APIRouter(prefix="/api")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(status_code=401, detail="Invalid credentials")
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


@router.post("/auth/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/auth/logout")
async def logout():
    return {"message": "Logged out successfully"}


@router.get("/auth/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "created_at": current_user.created_at}


def get_polymarket_service(db: Session) -> PolymarketService:
    bot_service = BotService(db)
    api_url = bot_service.get_setting("polymarket_api_url", settings.POLYMARKET_API_URL)
    api_key = bot_service.get_setting("polymarket_api_key", "")
    api_secret = bot_service.get_setting("polymarket_api_secret", "")
    wallet_address = bot_service.get_setting("polymarket_wallet_address", "")
    return PolymarketService(
        api_url=api_url,
        api_key=api_key if api_key else None,
        api_secret=api_secret if api_secret else None,
        wallet_address=wallet_address if wallet_address else None,
    )


@router.get("/markets")
async def get_markets(db: Session = Depends(get_db)):
    service = get_polymarket_service(db)
    markets = await service.get_markets_with_prices(50)
    return markets


@router.get("/markets/{market_id}")
async def get_market(market_id: str, db: Session = Depends(get_db)):
    service = get_polymarket_service(db)
    market = await service.get_market(market_id)
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    return market


@router.post("/trade/buy")
async def buy_market(
    market_id: str,
    market_question: str,
    side: str,
    amount: float,
    token_id: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = get_polymarket_service(db)

    if not token_id:
        market = await service.get_market(market_id)
        if market:
            tokens = market.get("tokens", [])
            token = next(
                (
                    t
                    for t in tokens
                    if t.get("outcome") == ("Yes" if side == "yes" else "No")
                ),
                None,
            )
            if token:
                token_id = token.get("token_id")

    if token_id:
        price_data = await service.get_price(token_id)
        price = price_data.get("yes_price" if side == "yes" else "no_price", 0.5)
        result = await service.place_order(token_id, side, amount, price)
    else:
        price = 0.5
        result = {"success": False, "error": "Token ID required for trading"}

    trade = Trade(
        market_id=market_id,
        market_question=market_question,
        side=TradeSide.YES if side == "yes" else TradeSide.NO,
        amount=amount,
        price=price,
        tx_hash=result.get("data", {}).get("orderID")
        if result.get("success")
        else None,
        status=TradeStatus.COMPLETED if result.get("success") else TradeStatus.FAILED,
        error_message=result.get("error"),
    )
    db.add(trade)

    position = Position(
        market_id=market_id,
        market_question=market_question,
        side=TradeSide.YES if side == "yes" else TradeSide.NO,
        amount=amount,
        entry_price=price,
        current_price=price,
    )
    db.add(position)
    db.commit()

    return result


@router.post("/trade/sell")
async def sell_position(
    position_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    position = (
        db.query(Position)
        .filter(Position.id == position_id, Position.is_open == True)
        .first()
    )
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    service = get_polymarket_service(db)
    result = {"success": False, "error": "Selling requires token_id"}

    position.is_open = False
    position.pnl = (position.current_price - position.entry_price) * position.amount
    db.commit()

    return {"success": True, "position": position}


@router.get("/positions")
async def get_positions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    positions = db.query(Position).filter(Position.is_open == True).all()
    return [
        {
            "id": p.id,
            "market_id": p.market_id,
            "market_question": p.market_question,
            "side": p.side.value,
            "amount": p.amount,
            "entry_price": p.entry_price,
            "current_price": p.current_price,
            "pnl": p.pnl,
            "created_at": p.created_at,
        }
        for p in positions
    ]


@router.get("/trades")
async def get_trades(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trades = db.query(Trade).order_by(Trade.created_at.desc()).limit(limit).all()
    return [
        {
            "id": t.id,
            "market_id": t.market_id,
            "market_question": t.market_question,
            "side": t.side.value,
            "amount": t.amount,
            "price": t.price,
            "tx_hash": t.tx_hash,
            "status": t.status.value,
            "created_at": t.created_at,
        }
        for t in trades
    ]


@router.get("/ai/config")
async def get_ai_config(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    config = db.query(AISettings).first()
    if not config:
        config = AISettings()
        db.add(config)
        db.commit()
        db.refresh(config)

    return {
        "provider": config.provider,
        "model": config.model,
        "prompt_template": config.prompt_template,
        "enabled": config.enabled,
        "ollama_url": config.ollama_url,
        "lmstudio_url": config.lmstudio_url,
        "has_openrouter_key": bool(config.openrouter_api_key),
        "has_gemini_key": bool(config.gemini_api_key),
    }


@router.post("/ai/config")
async def update_ai_config(
    provider: str = None,
    model: str = None,
    prompt_template: str = None,
    enabled: bool = None,
    ollama_url: str = None,
    lmstudio_url: str = None,
    openrouter_api_key: str = None,
    gemini_api_key: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = db.query(AISettings).first()
    if not config:
        config = AISettings()
        db.add(config)

    if provider is not None:
        config.provider = provider
    if model is not None:
        config.model = model
    if prompt_template is not None:
        config.prompt_template = prompt_template
    if enabled is not None:
        config.enabled = enabled
    if ollama_url is not None:
        config.ollama_url = ollama_url
    if lmstudio_url is not None:
        config.lmstudio_url = lmstudio_url
    if openrouter_api_key is not None:
        config.openrouter_api_key = openrouter_api_key
    if gemini_api_key is not None:
        config.gemini_api_key = gemini_api_key

    db.commit()
    return {"success": True}


@router.post("/ai/analyze")
async def analyze_market(
    market_id: str,
    market_question: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = get_polymarket_service(db)
    market = await service.get_market(market_id)
    prices = {"yes_price": 0.5, "no_price": 0.5}

    if market:
        tokens = market.get("tokens", [])
        yes_token = next((t for t in tokens if t.get("outcome") == "Yes"), None)
        if yes_token:
            token_prices = await service.get_price(yes_token.get("token_id", ""))
            prices = token_prices

    ai_service = AIService(db)
    result = await ai_service.analyze_market(market_question, prices)

    return {"decision": result, "prices": prices}


@router.post("/ai/trade")
async def ai_trade(
    market_id: str,
    market_question: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ai_service = AIService(db)
    if not ai_service.settings.enabled:
        return {"success": False, "error": "AI trading is not enabled"}

    service = get_polymarket_service(db)
    market = await service.get_market(market_id)
    prices = {"yes_price": 0.5, "no_price": 0.5}
    token_id = None

    if market:
        tokens = market.get("tokens", [])
        yes_token = next((t for t in tokens if t.get("outcome") == "Yes"), None)
        if yes_token:
            token_id = yes_token.get("token_id")
            token_prices = await service.get_price(token_id)
            prices = token_prices

    decision = await ai_service.analyze_market(market_question, prices)

    if decision in ["YES", "NO"] and token_id:
        side = "yes" if decision == "YES" else "no"
        bot_service = BotService(db)
        stake = bot_service.get_setting("stake_amount", 10.0)

        result = await service.place_order(
            token_id,
            side,
            stake,
            prices.get("yes_price" if side == "yes" else "no_price", 0.5),
        )

        trade = Trade(
            market_id=market_id,
            market_question=market_question,
            side=TradeSide.YES if side == "yes" else TradeSide.NO,
            amount=stake,
            price=prices.get("yes_price" if side == "yes" else "no_price", 0.5),
            status=TradeStatus.COMPLETED
            if result.get("success")
            else TradeStatus.FAILED,
        )
        db.add(trade)
        db.commit()

        return {"success": True, "decision": decision, "trade": result}

    return {"success": True, "decision": decision, "message": "AI decided to hold"}


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    positions = db.query(Position).filter(Position.is_open == True).all()

    total_invested = sum(p.amount * p.entry_price for p in positions)
    total_pnl = sum(p.pnl for p in positions)

    bot_service = BotService(db)
    bot_status = bot_service.get_bot_status()

    trades_today = (
        db.query(Trade)
        .filter(
            Trade.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
        )
        .count()
    )

    return {
        "total_positions": len(positions),
        "total_invested": round(total_invested, 2),
        "total_pnl": round(total_pnl, 2),
        "trades_today": trades_today,
        "bot_running": bot_status["running"],
        "auto_trade": bot_status["auto_trade"],
        "stake_amount": bot_status["stake_amount"],
    }


@router.get("/bot/status")
async def get_bot_status(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    bot_service = BotService(db)
    return bot_service.get_bot_status()


@router.post("/bot/start")
async def start_bot(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    bot_service = BotService(db)
    bot_service.set_bot_status(running=True)
    return {"success": True, "running": True}


@router.post("/bot/stop")
async def stop_bot(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    bot_service = BotService(db)
    bot_service.set_bot_status(running=False)
    return {"success": True, "running": False}


@router.post("/bot/settings")
async def update_bot_settings(
    auto_trade: bool = None,
    stake_amount: float = None,
    selected_markets: List[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bot_service = BotService(db)
    bot_service.set_bot_status(auto_trade=auto_trade, stake_amount=stake_amount)
    if selected_markets is not None:
        bot_service.set_setting("selected_markets", selected_markets)
    return {"success": True}


@router.get("/polymarket/config")
async def get_polymarket_config(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    bot_service = BotService(db)
    return {
        "api_url": bot_service.get_setting(
            "polymarket_api_url", "https://clob.polymarket.com"
        ),
        "api_key": bot_service.get_setting("polymarket_api_key", ""),
        "api_secret": bot_service.get_setting("polymarket_api_secret", ""),
        "wallet_address": bot_service.get_setting("polymarket_wallet_address", ""),
    }


@router.post("/polymarket/config")
async def update_polymarket_config(
    api_url: str = None,
    api_key: str = None,
    api_secret: str = None,
    wallet_address: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bot_service = BotService(db)
    if api_url is not None:
        bot_service.set_setting("polymarket_api_url", api_url)
    if api_key is not None:
        bot_service.set_setting("polymarket_api_key", api_key)
    if api_secret is not None:
        bot_service.set_setting("polymarket_api_secret", api_secret)
    if wallet_address is not None:
        bot_service.set_setting("polymarket_wallet_address", wallet_address)
    return {"success": True}


@router.get("/polymarket/balance")
async def get_balance(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    service = get_polymarket_service(db)
    balance = await service.get_balance()
    return balance


@router.post("/polymarket/test")
async def test_polymarket_connection(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    service = get_polymarket_service(db)
    try:
        markets = await service.get_markets(1)
        return {
            "success": True,
            "message": "Connection successful",
            "markets_count": len(markets),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.append(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


@router.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
