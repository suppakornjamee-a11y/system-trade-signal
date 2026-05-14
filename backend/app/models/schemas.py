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


class PaperDailyPnL(BaseModel):
    date: str
    equity: float
    pnl: float
    pnl_pct: float


class PaperPosition(BaseModel):
    id: int
    symbol: str
    name: str
    side: str  # long | short
    bucket: str  # momentum | quality
    bucket_label: str
    quantity: float
    entry_price: float
    current_price: float
    market_value: float
    risk_amount: float
    risk_pct: float
    allocation_pct: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    stop_loss: float
    target: float
    probability_pct: float
    status: str  # open | target_near | stop_near
    opened_at: str


class PaperTrade(BaseModel):
    id: str
    time: str
    symbol: str
    side: str
    bucket: str
    event_type: str  # open | close
    quantity: float
    price: float
    status: str
    reason: str
    pnl: Optional[float] = None


class PaperTradingSummary(BaseModel):
    mode: str
    market: str
    currency: str
    generated_at: str
    market_status: dict
    starting_cash: float
    cash: float
    equity: float
    invested: float
    daily_pnl: float
    daily_pnl_pct: float
    open_positions: int
    win_rate_pct: float
    max_drawdown_pct: float
    bucket_allocation: dict
    positions: list[PaperPosition]
    recent_trades: list[PaperTrade]
    daily: list[PaperDailyPnL]
