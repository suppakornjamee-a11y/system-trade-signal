import re
import time
import math
import yfinance as yf
import pandas as pd
from .. import cache as _cache
from ..config import BASE_DIR, settings


YFINANCE_CACHE_DIR = BASE_DIR / ".cache" / "yfinance"
YFINANCE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
yf.set_tz_cache_location(str(YFINANCE_CACHE_DIR))


def _ticker(symbol: str) -> yf.Ticker:
    return yf.Ticker(symbol)


def _fast_info_value(info, *names, default=None):
    for name in names:
        try:
            if isinstance(info, dict):
                value = info.get(name)
            else:
                value = getattr(info, name)
        except Exception:
            continue
        if value is not None:
            return value
    return default


def get_usd_thb_rate() -> float:
    cached = _cache.get("fx:usd_thb", 300)
    if cached:
        return float(cached)

    hist = _ticker("THB=X").history(period="5d", interval="1d", timeout=8)
    if hist.empty:
        raise ValueError("No USD/THB FX data")

    rate = float(hist["Close"].iloc[-1])
    _cache.set("fx:usd_thb", rate)
    return rate


def get_quote(symbol: str) -> dict:
    cached = _cache.get(f"quote:{symbol}", settings.cache_ttl_seconds)
    if cached:
        return cached

    t = _ticker(symbol)
    try:
        info = t.fast_info
    except Exception:
        info = {}

    hist = t.history(period="2d", interval="1d", timeout=8)
    if hist.empty:
        hist = t.history(period="5d", interval="1d", timeout=8)

    intraday = pd.DataFrame()
    if hist.empty:
        intraday = t.history(period="1d", interval="5m", timeout=8)

    if not hist.empty:
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else float(hist["Close"].iloc[-1])
        current = float(hist["Close"].iloc[-1])
        volume = int(hist["Volume"].iloc[-1])
    elif not intraday.empty:
        current = float(intraday["Close"].iloc[-1])
        prev_close = float(intraday["Close"].iloc[0])
        volume = int(intraday["Volume"].sum())
    else:
        current = float(_fast_info_value(info, "last_price", "regular_market_price", default=0) or 0)
        prev_close = float(_fast_info_value(info, "previous_close", default=current) or current)
        volume = int(_fast_info_value(info, "last_volume", default=0) or 0)
        if not math.isfinite(current) or current <= 0:
            raise ValueError(f"No data for {symbol}")

    change = current - prev_close
    change_pct = (change / prev_close) * 100 if prev_close else 0.0

    result = {
        "symbol": symbol.upper(),
        "name": _fast_info_value(info, "long_name", "short_name", default=symbol),
        "price": round(current, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "volume": volume,
        "avg_volume": int(_fast_info_value(info, "three_month_average_volume", default=0) or 0),
        "market_cap": _fast_info_value(info, "market_cap", default=None),
    }

    _cache.set(f"quote:{symbol}", result)
    return result


def get_company_profile(symbol: str) -> dict:
    cached = _cache.get(f"profile:{symbol}", 3600)
    if cached:
        return cached

    info = _ticker(symbol).info or {}
    summary = info.get("longBusinessSummary") or ""
    result = {
        "symbol": symbol.upper(),
        "name": info.get("longName") or info.get("shortName") or symbol.upper(),
        "sector": info.get("sector") or "",
        "industry": info.get("industry") or "",
        "description": summary,
    }

    _cache.set(f"profile:{symbol}", result)
    return result


def get_candles(symbol: str, period: str = "1d", interval: str = "5m") -> list[dict]:
    key = f"candles:{symbol}:{period}:{interval}"
    cached = _cache.get(key, settings.cache_ttl_seconds)
    if cached:
        return cached

    t = _ticker(symbol)
    hist = t.history(period=period, interval=interval, timeout=8)

    if hist.empty:
        return []

    bars = []
    for ts, row in hist.iterrows():
        bars.append({
            "time": int(ts.timestamp()),
            "open": round(float(row["Open"]), 4),
            "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4),
            "close": round(float(row["Close"]), 4),
            "volume": int(row["Volume"]),
        })

    _cache.set(key, bars)
    return bars


def get_history(symbol: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
    key = f"history:{symbol}:{period}:{interval}"
    cached = _cache.get(key, 60)
    if cached is not None:
        return cached

    t = _ticker(symbol)
    df = t.history(period=period, interval=interval, timeout=8)
    df.columns = [c.lower() for c in df.columns]
    if not df.empty:
        _cache.set(key, df)
    return df


def _news_is_relevant(symbol: str, news_item: dict) -> bool:
    # Strip market suffix: PTT.BK → PTT, 600519.SS → 600519
    clean = re.sub(r"\.(BK|HK|SS|SZ)$", "", symbol.upper())

    # Newer yfinance: entities list with type="ticker"
    entities = news_item.get("entities") or []
    if entities:
        tickers = {e.get("term", "").upper() for e in entities if e.get("type") == "ticker"}
        if tickers:
            return clean in tickers

    # Fallback: relatedTickers inside content
    related = news_item.get("content", {}).get("relatedTickers") or []
    if related:
        return clean in {re.sub(r"\.\w+$", "", r.upper()) for r in related}

    # Last resort: symbol must appear as a whole word in the title
    title = news_item.get("content", {}).get("title", "").upper()
    return bool(re.search(r"\b" + re.escape(clean) + r"\b", title))


def get_news(symbol: str) -> list[dict]:
    cached = _cache.get(f"news:{symbol}", 120)
    if cached:
        return cached

    t = _ticker(symbol)
    raw = t.news or []
    items = []
    for n in raw:
        if not _news_is_relevant(symbol, n):
            continue
        items.append({
            "title": n.get("content", {}).get("title", ""),
            "publisher": n.get("content", {}).get("provider", {}).get("displayName", ""),
            "link": n.get("content", {}).get("canonicalUrl", {}).get("url", ""),
            "published_at": n.get("content", {}).get("pubDate", 0),
        })
        if len(items) >= 10:
            break

    _cache.set(f"news:{symbol}", items)
    return items
