from pydantic import BaseModel
from typing import Optional


class NewsItem(BaseModel):
    title: str
    publisher: str
    link: str
    published_at: int
    sentiment: str  # bullish | bearish | neutral


class TechnicalData(BaseModel):
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    ma20: Optional[float] = None
    ma50: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None
    atr: Optional[float] = None
    support: float
    resistance: float
    trend: str  # bullish | bearish | neutral


class TradeSetup(BaseModel):
    direction: str  # long | short
    entry: float
    entry_zone_low: float
    entry_zone_high: float
    target: float
    stop_loss: float
    risk_reward: float
    probability_pct: float
    tech_score: float
    news_score: float
    volume_score: float
    action: str  # ready | wait_pullback | wait_bounce
    entry_distance_pct: float
    target_room_pct: float


class StockSummary(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    volume: int
    avg_volume: int
    volume_ratio: float
    market_cap: Optional[float] = None
    news_sentiment: str  # bullish | bearish | neutral
    news_count: int
    signal: str  # bullish | bearish | neutral
    trade_setup: TradeSetup


class CandleBar(BaseModel):
    time: int  # unix timestamp
    open: float
    high: float
    low: float
    close: float
    volume: int


class StockDetail(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    volume: int
    avg_volume: int
    volume_ratio: float
    market_cap: Optional[float] = None
    technical: TechnicalData
    trade_setup: TradeSetup
    news: list[NewsItem]
    candles: list[CandleBar]


class PriceUpdate(BaseModel):
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: int
    timestamp: int
