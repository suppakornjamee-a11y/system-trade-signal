from datetime import datetime, time
from zoneinfo import ZoneInfo


MARKET_SESSIONS = {
    "us": {
        "timezone": "America/New_York",
        "sessions": ((time(9, 30), time(16, 0)),),
    },
    "th": {
        "timezone": "Asia/Bangkok",
        "sessions": ((time(10, 0), time(12, 30)), (time(14, 30), time(16, 30))),
    },
    "cn": {
        "timezone": "Asia/Hong_Kong",
        "sessions": ((time(9, 30), time(12, 0)), (time(13, 0), time(16, 0))),
    },
    "gold": {
        "timezone": "America/New_York",
        "sessions": (),
    },
    "crypto": {
        "timezone": "UTC",
        "sessions": (),
    },
}


def is_market_open(market: str, now: datetime | None = None) -> bool:
    schedule = MARKET_SESSIONS.get(market.lower())
    if not schedule:
        return True

    local_now = (now or datetime.now(ZoneInfo("UTC"))).astimezone(ZoneInfo(schedule["timezone"]))
    if market.lower() == "crypto":
        return True
    if market.lower() == "gold":
        weekday = local_now.weekday()
        current_time = local_now.time()
        if weekday == 5:
            return False
        if weekday == 6:
            return current_time >= time(18, 0)
        if weekday == 4 and current_time >= time(17, 0):
            return False
        return not (time(17, 0) <= current_time < time(18, 0))

    if local_now.weekday() >= 5:
        return False

    current_time = local_now.time()
    return any(start <= current_time <= end for start, end in schedule["sessions"])


def market_status(market: str, now: datetime | None = None) -> dict:
    schedule = MARKET_SESSIONS.get(market.lower())
    if not schedule:
        return {"market": market, "is_open": True, "reason": "unknown_market"}

    local_now = (now or datetime.now(ZoneInfo("UTC"))).astimezone(ZoneInfo(schedule["timezone"]))
    return {
        "market": market,
        "is_open": is_market_open(market, local_now),
        "local_time": local_now.isoformat(timespec="seconds"),
        "timezone": schedule["timezone"],
    }
