from fastapi import APIRouter, HTTPException, Query

from ..services.signal_engine import build_trade_signals
from ..services.signal_scheduler import scan_and_notify, scan_premarket_news_and_notify
from ..services.market_briefing import build_premarket_briefing, format_premarket_message
from ..services.telegram_service import send_telegram_message

router = APIRouter()


@router.get("")
def list_signals(market: str = Query("us", pattern="^(us|th|cn|gold|crypto)$")):
    try:
        return build_trade_signals(market=market)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/scan")
async def scan_signals_and_notify():
    try:
        return await scan_and_notify()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/premarket")
def preview_premarket_briefing(market: str = Query("us", pattern="^(us|th|cn)$")):
    try:
        briefing = build_premarket_briefing(market)
        return {**briefing, "telegram_message": format_premarket_message(briefing)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/premarket/scan")
async def scan_premarket_news():
    try:
        return await scan_premarket_news_and_notify()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/premarket/send")
async def send_premarket_briefing(market: str = Query("us", pattern="^(us|th|cn)$")):
    try:
        briefing = build_premarket_briefing(market)
        response = await send_telegram_message(format_premarket_message(briefing))
        return {"sent": True, "market": market, "bias": briefing["bias"], "telegram": response}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
