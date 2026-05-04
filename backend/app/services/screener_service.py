from .. import cache as _cache
from ..config import settings
from .stock_service import get_quote
from .technical_analysis import analyze
from .news_service import get_news_with_sentiment
from .probability_engine import calculate_trade_setup

MARKET_WATCHLISTS: dict[str, list[str]] = {
    "us": [
        # Mega-cap tech
        "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "AMD",
        # Semiconductors
        "INTC", "AVGO", "QCOM", "MU", "SMCI",
        # Finance
        "JPM", "BAC", "GS", "MS", "V", "MA",
        # Energy
        "XOM", "CVX",
        # Healthcare
        "JNJ", "PFE", "MRNA",
        # Retail / Consumer
        "WMT", "HD", "NKE", "SBUX",
        # Popular retail / high-momentum
        "PLTR", "SOFI", "MARA", "RIOT", "COIN", "GME",
        # ETFs
        "SPY", "QQQ", "IWM", "SOXS", "TQQQ",
    ],
    "th": [
        "PTT.BK", "SCB.BK", "ADVANC.BK", "AOT.BK", "CPALL.BK",
        "BDMS.BK", "SCC.BK", "BBL.BK", "KBANK.BK", "KTB.BK",
        "TRUE.BK", "MINT.BK", "CPN.BK", "GULF.BK", "GPSC.BK",
        "IVL.BK", "PTTGC.BK", "TOP.BK", "DELTA.BK", "OSP.BK",
        "HANA.BK", "BH.BK", "CPAXT.BK", "SPRC.BK",
    ],
    "cn": [
        "600519.SS",  # Kweichow Moutai 贵州茅台
        "600036.SS",  # China Merchants Bank 招商银行
        "601318.SS",  # Ping An Insurance 中国平安
        "300750.SZ",  # CATL 宁德时代
        "002594.SZ",  # BYD 比亚迪
        "601857.SS",  # PetroChina 中国石油
        "600941.SS",  # China Mobile 中国移动
        "601398.SS",  # ICBC 工商银行
        "600900.SS",  # China Yangtze Power 长江电力
        "601012.SS",  # LONGi Green Energy 隆基绿能
        "002415.SZ",  # Hikvision 海康威视
        "600030.SS",  # CITIC Securities 中信证券
        "601088.SS",  # China Shenhua Energy 中国神华
        "000858.SZ",  # Wuliangye 五粮液
        "600309.SS",  # Wanhua Chemical 万华化学
    ],
}

MARKET_THRESHOLDS = {
    "us": {"min_change_pct": 1.2, "min_vol_ratio": 1.1},
    "th": {"min_change_pct": 0.8, "min_vol_ratio": 1.0},
    "cn": {"min_change_pct": 0.8, "min_vol_ratio": 1.0},
}

TOP_N = 12


def _momentum_rank(summary: dict) -> int:
    """Score 1-5 for 2-3 day swing trading potential (หุ้นซิ่ง)."""
    score = 0

    # 1. Price momentum (0-3 pts)
    chg = abs(summary["change_pct"])
    if chg >= 7:
        score += 3
    elif chg >= 4:
        score += 2
    elif chg >= 2:
        score += 1

    # 2. Volume surge (0-3 pts)
    vol = summary["volume_ratio"]
    if vol >= 3:
        score += 3
    elif vol >= 2:
        score += 2
    elif vol >= 1.5:
        score += 1

    # 3. News catalyst (0-2 pts)
    has_clear_signal = summary["news_sentiment"] != "neutral"
    has_enough_news = summary["news_count"] >= 3
    if has_clear_signal and has_enough_news:
        score += 2
    elif has_clear_signal or has_enough_news:
        score += 1

    # 4. Win probability (0-2 pts)
    prob = summary["trade_setup"]["probability_pct"]
    if prob >= 65:
        score += 2
    elif prob >= 55:
        score += 1

    # Convert 0-10 → 1-5
    if score <= 2:
        return 1
    if score <= 4:
        return 2
    if score <= 6:
        return 3
    if score <= 8:
        return 4
    return 5


def _interest_score(summary: dict) -> float:
    rank = summary.get("momentum_rank", 1)
    return (
        rank * 2.0
        + abs(summary["change_pct"]) * 0.4
        + summary["news_count"] * 0.2
        + summary["volume_ratio"] * 0.1
    )


def _build_stock_summary(symbol: str, market: str) -> dict | None:
    thresholds = MARKET_THRESHOLDS.get(market, MARKET_THRESHOLDS["us"])
    try:
        quote = get_quote(symbol)
        avg_vol = quote.get("avg_volume", 1) or 1
        volume_ratio = quote["volume"] / avg_vol

        if (
            abs(quote["change_pct"]) < thresholds["min_change_pct"]
            and volume_ratio < thresholds["min_vol_ratio"]
        ):
            return None

        ta = analyze(symbol)
        if not ta:
            return None

        news, news_sentiment, news_score = get_news_with_sentiment(symbol)
        setup = calculate_trade_setup(ta, quote, news_score, news_sentiment)

        trend = ta.get("trend", "neutral")
        if news_sentiment == "bullish" and trend in ("bullish", "neutral"):
            signal = "bullish"
        elif news_sentiment == "bearish" and trend in ("bearish", "neutral"):
            signal = "bearish"
        else:
            signal = "neutral"

        summary = {
            "symbol": symbol,
            "name": quote["name"],
            "price": quote["price"],
            "change": quote["change"],
            "change_pct": quote["change_pct"],
            "volume": quote["volume"],
            "avg_volume": avg_vol,
            "volume_ratio": round(volume_ratio, 2),
            "market_cap": quote.get("market_cap"),
            "news_sentiment": news_sentiment,
            "news_count": len(news),
            "signal": signal,
            "trade_setup": setup,
            "market": market,
        }
        summary["momentum_rank"] = _momentum_rank(summary)
        return summary
    except Exception:
        return None


def get_screener_results(market: str = "us") -> list[dict]:
    cache_key = f"screener:{market}:today"
    cached = _cache.get(cache_key, settings.screener_cache_ttl_seconds)
    if cached:
        return cached

    watchlist = MARKET_WATCHLISTS.get(market, MARKET_WATCHLISTS["us"])
    results = []
    for symbol in watchlist:
        summary = _build_stock_summary(symbol, market)
        if summary:
            results.append(summary)

    results.sort(key=_interest_score, reverse=True)
    top = results[:TOP_N]
    _cache.set(cache_key, top)
    return top
