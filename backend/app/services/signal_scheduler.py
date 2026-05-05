import asyncio
import logging

from ..config import settings
from .signal_engine import (
    build_trade_signals,
    format_signal_message,
    mark_signal_sent,
    should_send_signal,
)
from .telegram_service import send_telegram_message

logger = logging.getLogger(__name__)


def _configured_markets() -> list[str]:
    markets = [m.strip().lower() for m in settings.signal_markets.split(",")]
    return [m for m in markets if m]


async def scan_and_notify() -> dict:
    sent = []
    skipped = []
    errors = []

    for market in _configured_markets():
        try:
            signals = await asyncio.to_thread(build_trade_signals, market=market)
        except Exception as exc:
            errors.append({"market": market, "error": str(exc)})
            continue

        for signal in signals:
            if not should_send_signal(signal):
                skipped.append({"symbol": signal["symbol"], "reason": "cooldown"})
                continue

            try:
                await send_telegram_message(format_signal_message(signal))
                mark_signal_sent(signal)
                sent.append({"symbol": signal["symbol"], "score": signal["score"]})
            except Exception as exc:
                errors.append({"symbol": signal["symbol"], "error": str(exc)})

    return {"sent": sent, "skipped": skipped, "errors": errors}


async def run_signal_scheduler() -> None:
    await asyncio.sleep(30)
    while True:
        try:
            await scan_and_notify()
        except Exception:
            logger.exception("Signal scheduler failed")
        await asyncio.sleep(settings.signal_poll_interval_seconds)
