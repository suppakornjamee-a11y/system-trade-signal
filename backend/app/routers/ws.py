import asyncio
import json
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.stock_service import get_quote

router = APIRouter()

POLL_INTERVAL = 30  # seconds — yfinance free tier delay


@router.websocket("/ws/{symbol}")
async def websocket_price(websocket: WebSocket, symbol: str):
    await websocket.accept()
    symbol = symbol.upper()
    try:
        while True:
            try:
                quote = get_quote(symbol)
                payload = {
                    "symbol": symbol,
                    "price": quote["price"],
                    "change": quote["change"],
                    "change_pct": quote["change_pct"],
                    "volume": quote["volume"],
                    "timestamp": int(time.time()),
                }
                await websocket.send_text(json.dumps(payload))
            except Exception as e:
                await websocket.send_text(json.dumps({"error": str(e)}))
            await asyncio.sleep(POLL_INTERVAL)
    except WebSocketDisconnect:
        pass
