import html
import math
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import yfinance as yf

from .. import cache as _cache
from ..config import settings
from .market_hours import MARKET_SESSIONS


MARKET_BRIEFING_SYMBOLS: dict[str, list[tuple[str, str]]] = {
    "us": [
        ("ES=F", "S&P 500 Futures"),
        ("NQ=F", "Nasdaq Futures"),
        ("YM=F", "Dow Futures"),
        ("^VIX", "VIX"),
        ("DX-Y.NYB", "Dollar Index"),
        ("^TNX", "US 10Y Yield"),
    ],
    "th": [
        ("^SET.BK", "SET Index"),
        ("THB=X", "USD/THB"),
        ("CL=F", "Crude Oil"),
        ("GC=F", "Gold Futures"),
        ("^HSI", "Hang Seng"),
        ("000001.SS", "Shanghai Composite"),
    ],
    "cn": [
        ("000001.SS", "Shanghai Composite"),
        ("399001.SZ", "Shenzhen Component"),
        ("^HSI", "Hang Seng"),
        ("CNH=X", "USD/CNH"),
        ("BABA", "Alibaba ADR"),
        ("KWEB", "China Internet ETF"),
    ],
}

MARKET_NEWS_TICKERS = {
    "us": "^GSPC",
    "th": "^SET.BK",
    "cn": "000001.SS",
}

MARKET_LABELS = {
    "us": "ตลาดสหรัฐ",
    "th": "ตลาดไทย",
    "cn": "ตลาดจีน/HK",
}

POSITIVE_WORDS = {
    "rally", "rallies", "surge", "surges", "gain", "gains", "higher", "rise", "rises",
    "beat", "beats", "optimism", "approval", "approved", "record", "rebound", "eases",
    "cuts rates", "stimulus", "strong", "growth", "upgrade", "upgraded",
}

NEGATIVE_WORDS = {
    "fall", "falls", "drop", "drops", "lower", "selloff", "sell-off", "slump", "plunge",
    "miss", "misses", "risk", "risks", "concern", "concerns", "tariff", "inflation",
    "yields rise", "warning", "downgrade", "downgraded", "lawsuit", "probe",
}


def _configured_premarket_markets() -> list[str]:
    markets = [m.strip().lower() for m in settings.premarket_news_markets.split(",")]
    return [m for m in markets if m in MARKET_BRIEFING_SYMBOLS]


def _first_session_start(market: str, now: datetime | None = None) -> datetime | None:
    schedule = MARKET_SESSIONS.get(market)
    if not schedule or not schedule["sessions"]:
        return None

    local_now = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo(schedule["timezone"]))
    start_time = schedule["sessions"][0][0]
    candidate = local_now.replace(
        hour=start_time.hour,
        minute=start_time.minute,
        second=0,
        microsecond=0,
    )

    if local_now.weekday() >= 5 or local_now >= candidate:
        days_ahead = 1
        while (local_now + timedelta(days=days_ahead)).weekday() >= 5:
            days_ahead += 1
        target = local_now + timedelta(days=days_ahead)
        candidate = target.replace(
            hour=start_time.hour,
            minute=start_time.minute,
            second=0,
            microsecond=0,
        )

    return candidate


def should_send_premarket_briefing(market: str, now: datetime | None = None) -> tuple[bool, dict]:
    open_at = _first_session_start(market, now)
    if open_at is None:
        return False, {"market": market, "reason": "unsupported_market"}

    local_now = (now or datetime.now(timezone.utc)).astimezone(open_at.tzinfo)
    send_from = open_at - timedelta(minutes=settings.premarket_news_minutes_before_open)
    send_until = send_from + timedelta(minutes=settings.premarket_news_window_minutes)
    is_window = send_from <= local_now <= send_until
    sent_key = f"premarket:sent:{market}:{open_at.date().isoformat()}"
    already_sent = _cache.get(sent_key, settings.premarket_news_dedupe_ttl_hours * 60 * 60) is not None

    return is_window and not already_sent, {
        "market": market,
        "local_time": local_now.isoformat(timespec="seconds"),
        "open_at": open_at.isoformat(timespec="seconds"),
        "send_from": send_from.isoformat(timespec="seconds"),
        "send_until": send_until.isoformat(timespec="seconds"),
        "already_sent": already_sent,
        "is_window": is_window,
    }


def mark_premarket_briefing_sent(market: str, open_at: str | None = None) -> None:
    date_text = open_at[:10] if open_at else datetime.now(timezone.utc).date().isoformat()
    _cache.set(f"premarket:sent:{market}:{date_text}", int(time.time()))


def _history_snapshot(symbol: str, label: str) -> dict | None:
    try:
        hist = yf.Ticker(symbol).history(period="5d", interval="1d", timeout=8)
    except Exception:
        return None

    if hist.empty:
        return None

    current = float(hist["Close"].iloc[-1])
    previous = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else current
    if not math.isfinite(current) or not math.isfinite(previous) or previous == 0:
        return None

    change_pct = (current - previous) / previous * 100
    return {
        "symbol": symbol,
        "label": label,
        "price": current,
        "change_pct": change_pct,
    }


def _latest_market_news(market: str, limit: int = 5) -> list[dict]:
    try:
        raw = yf.Ticker(MARKET_NEWS_TICKERS[market]).news or []
    except Exception:
        return []

    items = []
    for item in raw:
        content = item.get("content", {})
        title = content.get("title", "")
        if not title:
            continue
        items.append({
            "title": title,
            "publisher": content.get("provider", {}).get("displayName", ""),
        })
        if len(items) >= limit:
            break
    return items


def _headline_score(news: list[dict]) -> int:
    score = 0
    for item in news:
        title = item["title"].lower()
        score += sum(1 for word in POSITIVE_WORDS if word in title)
        score -= sum(1 for word in NEGATIVE_WORDS if word in title)
    return score


def _snapshot_score(market: str, snapshots: list[dict]) -> float:
    score = 0.0
    for item in snapshots:
        change = item["change_pct"]
        symbol = item["symbol"]
        if symbol in {"^VIX", "DX-Y.NYB", "^TNX", "THB=X", "CNH=X"}:
            score -= change * 0.8
        else:
            score += change
    if market == "th":
        score *= 0.9
    return score


def _direction(score: float) -> tuple[str, str, str]:
    if score >= 1.2:
        return "บวก", "เพิ่มความพร้อมฝั่งซื้อ แต่ยังรอจังหวะเปิดตลาด", "ถือต่อ/หาจังหวะสะสมเฉพาะตัวแข็ง"
    if score <= -1.2:
        return "ลบ", "ลดความเสี่ยงก่อน เปิดพอร์ตแบบตั้งรับ", "ลดไซซ์ เก็บเงินสด และรอให้ราคาเลือกทาง"
    return "กลาง", "ยังไม่ชัด ให้รอข้อมูลหลังเปิดตลาด", "ถือพอร์ตเดิมได้ แต่ยังไม่ควรไล่ราคา"


def _format_snapshot(item: dict) -> str:
    price = item["price"]
    if abs(price) >= 100:
        price_text = f"{price:,.2f}"
    else:
        price_text = f"{price:.4f}"
    return f"{html.escape(item['label'])}: {price_text} ({item['change_pct']:+.2f}%)"


def build_premarket_briefing(market: str) -> dict:
    snapshots = [
        snapshot
        for symbol, label in MARKET_BRIEFING_SYMBOLS[market]
        if (snapshot := _history_snapshot(symbol, label)) is not None
    ]
    news = _latest_market_news(market)
    combined_score = _snapshot_score(market, snapshots) + (_headline_score(news) * 0.35)
    bias, posture, portfolio_action = _direction(combined_score)

    risk_notes = []
    for item in snapshots:
        if item["symbol"] in {"^VIX", "^TNX"} and item["change_pct"] > 1:
            risk_notes.append(f"{item['label']} ขึ้น กดดันสินทรัพย์เสี่ยง")
        if item["symbol"] in {"THB=X", "CNH=X"} and item["change_pct"] > 0.4:
            risk_notes.append(f"{item['label']} แข็งฝั่งดอลลาร์ ระวังแรงขายในเอเชีย")

    return {
        "market": market,
        "label": MARKET_LABELS.get(market, market.upper()),
        "bias": bias,
        "score": round(combined_score, 2),
        "posture": posture,
        "portfolio_action": portfolio_action,
        "snapshots": snapshots,
        "news": news,
        "risk_notes": risk_notes[:3],
        "created_at": int(time.time()),
    }


def format_premarket_message(briefing: dict) -> str:
    snapshots = briefing["snapshots"][:6]
    news = briefing["news"][:5]
    snapshot_lines = [f"- {_format_snapshot(item)}" for item in snapshots] or ["- ยังดึงตัวชี้นำหลักไม่ได้ ใช้ข่าวและสัญญาณหลังเปิดประกอบ"]
    news_lines = [f"- {html.escape(item['title'])}" for item in news] or ["- ยังไม่มีข่าวตลาดล่าสุดจากแหล่งข้อมูล"]
    risk_notes = briefing.get("risk_notes") or ["ไม่มีสัญญาณเสี่ยงเด่นจากตัวชี้นำหลัก"]

    lines = [
        f"<b>ข่าวก่อนเปิดตลาด: {html.escape(briefing['label'])}</b>",
        f"ทิศทางเช้านี้: <b>{html.escape(briefing['bias'])}</b> | คะแนนภาพรวม {briefing['score']:+.2f}",
        html.escape(briefing["posture"]),
        "",
        f"แผนพอร์ต: <b>{html.escape(briefing['portfolio_action'])}</b>",
        "",
        "ตัวชี้นำ:",
        *snapshot_lines,
        "",
        "ข่าวที่ต้องรู้:",
        *news_lines,
        "",
        "ระวัง:",
        *[f"- {html.escape(note)}" for note in risk_notes],
    ]
    return "\n".join(lines)


def build_all_due_premarket_briefings(now: datetime | None = None) -> list[tuple[dict, dict]]:
    due = []
    for market in _configured_premarket_markets():
        should_send, timing = should_send_premarket_briefing(market, now)
        if should_send:
            due.append((build_premarket_briefing(market), timing))
    return due
