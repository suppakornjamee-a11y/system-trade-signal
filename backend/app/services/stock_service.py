import re
import time
import yfinance as yf
import pandas as pd
from .. import cache as _cache
from ..config import settings


def _ticker(symbol: str) -> yf.Ticker:
    return yf.Ticker(symbol)


def get_quote(symbol: str) -> dict:
    cached = _cache.get(f"quote:{symbol}", settings.cache_ttl_seconds)
    if cached:
        return cached

    t = _ticker(symbol)
    info = t.fast_info
    hist = t.history(period="2d", interval="1d")

    if hist.empty:
        raise ValueError(f"No data for {symbol}")

    prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else float(hist["Close"].iloc[-1])
    current = float(hist["Close"].iloc[-1])
    change = current - prev_close
    change_pct = (change / prev_close) * 100

    result = {
        "symbol": symbol.upper(),
        "name": getattr(info, "long_name", symbol),
        "price": round(current, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "volume": int(hist["Volume"].iloc[-1]),
        "avg_volume": int(getattr(info, "three_month_average_volume", 0) or 0),
        "market_cap": getattr(info, "market_cap", None),
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
    hist = t.history(period=period, interval=interval)

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
    df = t.history(period=period, interval=interval)
    df.columns = [c.lower() for c in df.columns]
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
