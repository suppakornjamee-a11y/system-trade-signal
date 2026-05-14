import asyncio
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import screener, stocks, ws, news, signals, paper_trading
from .services.signal_scheduler import run_signal_scheduler

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(screener.router, prefix="/api/screener", tags=["screener"])
app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(ws.router, tags=["websocket"])
app.include_router(news.router, prefix="/api/news", tags=["news"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(paper_trading.router, prefix="/api/paper-trading", tags=["paper-trading"])


@app.on_event("startup")
async def start_signal_scheduler():
    if settings.signal_notifications_enabled or settings.premarket_news_enabled:
        logger.info("Notification scheduler enabled")
        asyncio.create_task(run_signal_scheduler())
    else:
        logger.info("Notification scheduler disabled")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "git_commit": os.environ.get("RAILWAY_GIT_COMMIT_SHA", ""),
        "signals": {
            "notifications_enabled": settings.signal_notifications_enabled,
            "telegram_configured": bool(settings.telegram_bot_token and settings.telegram_chat_id),
            "markets": settings.signal_markets,
            "poll_interval_seconds": settings.signal_poll_interval_seconds,
            "cooldown_minutes": settings.signal_cooldown_minutes,
            "min_score": settings.signal_min_score,
            "min_risk_reward": settings.signal_min_risk_reward,
        },
        "premarket_news": {
            "enabled": settings.premarket_news_enabled,
            "markets": settings.premarket_news_markets,
            "minutes_before_open": settings.premarket_news_minutes_before_open,
            "window_minutes": settings.premarket_news_window_minutes,
        },
    }
