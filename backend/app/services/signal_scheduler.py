import asyncio
import logging

from ..config import settings
from .signal_engine import (
    build_trade_signals,
    format_signal_message,
    mark_signal_sent,
    should_send_signal,
)
from .market_hours import market_status
from .screener_service import get_last_screener_diagnostics
from .telegram_service import send_telegram_message

logger = logging.getLogger("uvicorn.error")


def _configured_markets() -> list[str]:
    markets = [m.strip().lower() for m in settings.signal_markets.split(",")]
    return [m for m in markets if m]


async def scan_and_notify() -> dict:
    sent = []
    skipped = []
    errors = []
    diagnostics = {}

    for market in _configured_markets():
        status = market_status(market)
        if not status["is_open"]:
            skipped.append({"market": market, "reason": "market_closed", "local_time": status.get("local_time")})
            diagnostics[market] = {"market_hours": status}
            continue

        try:
            signals = await asyncio.to_thread(build_trade_signals, market=market)
            diagnostics[market] = {
                "market_hours": status,
                "screener": get_last_screener_diagnostics(market),
            }
        except Exception as exc:
            errors.append({"market": market, "error": str(exc)})
            continue

        for signal in signals:
            if not should_send_signal(signal):
                skipped.append({"symbol": signal["symbol"], "reason": "already_sent"})
                continue

            try:
                await send_telegram_message(format_signal_message(signal))
                mark_signal_sent(signal)
                sent.append({"symbol": signal["symbol"], "score": signal["score"]})
            except Exception as exc:
                errors.append({"symbol": signal["symbol"], "error": str(exc)})

    result = {"sent": sent, "skipped": skipped, "errors": errors, "diagnostics": diagnostics}
    logger.info("Signal scan finished: %s", result)
    return result


async def run_signal_scheduler() -> None:
    while True:
        try:
            await scan_and_notify()
        except Exception:
            logger.exception("Signal scheduler failed")
        await asyncio.sleep(settings.signal_poll_interval_seconds)
