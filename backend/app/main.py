import asyncio
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import screener, stocks, ws, news, signals
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


@app.on_event("startup")
async def start_signal_scheduler():
    if settings.signal_notifications_enabled:
        logger.info("Signal notification scheduler enabled")
        asyncio.create_task(run_signal_scheduler())
    else:
        logger.info("Signal notification scheduler disabled")


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
    }
