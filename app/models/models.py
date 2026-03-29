from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class TradeSide(str, enum.Enum):
    YES = "yes"
    NO = "no"


class TradeStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    password_hash = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(String(255), index=True)
    market_question = Column(Text)
    side = Column(Enum(TradeSide))
    amount = Column(Float)
    entry_price = Column(Float)
    current_price = Column(Float, default=0.0)
    pnl = Column(Float, default=0.0)
    is_open = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(String(255), index=True)
    market_question = Column(Text)
    side = Column(Enum(TradeSide))
    amount = Column(Float)
    price = Column(Float)
    tx_hash = Column(String(255), nullable=True)
    status = Column(Enum(TradeStatus), default=TradeStatus.PENDING)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AISettings(Base):
    __tablename__ = "ai_settings"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), default="ollama")
    api_key = Column(String(255), nullable=True)
    model = Column(String(100), default="llama2")
    prompt_template = Column(
        Text,
        default="You are a trading assistant. Analyze this market and decide: Should I buy YES or NO? Just answer with YES, NO, or HOLD.",
    )
    enabled = Column(Boolean, default=False)
    ollama_url = Column(String(255), default="http://localhost:11434")
    lmstudio_url = Column(String(255), default="http://localhost:1234/v1")
    openrouter_api_key = Column(String(255), nullable=True)
    gemini_api_key = Column(String(255), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BotSettings(Base):
    __tablename__ = "bot_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True)
    value = Column(Text)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MarketCache(Base):
    __tablename__ = "market_cache"

    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(String(255), unique=True, index=True)
    question = Column(Text)
    description = Column(Text)
    volume = Column(Float)
    yes_price = Column(Float)
    no_price = Column(Float)
    end_date = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
