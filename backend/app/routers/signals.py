from fastapi import APIRouter, HTTPException, Query

from ..services.signal_engine import build_trade_signals
from ..services.signal_scheduler import scan_and_notify

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
