import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import screener, stocks, ws, news, signals
from .services.signal_scheduler import run_signal_scheduler

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
        asyncio.create_task(run_signal_scheduler())


@app.get("/health")
def health():
    return {"status": "ok"}
