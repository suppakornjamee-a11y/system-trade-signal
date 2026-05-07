from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
import logging

from .. import cache as _cache
from ..config import settings
from .stock_service import get_quote, get_usd_thb_rate
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
    ],
    "th": [
        "PTT.BK", "SCB.BK", "ADVANC.BK", "AOT.BK", "CPALL.BK",
        "BDMS.BK", "SCC.BK", "BBL.BK", "KBANK.BK", "KTB.BK",
        "TRUE.BK", "MINT.BK", "CPN.BK", "GULF.BK", "GPSC.BK",
        "IVL.BK", "PTTGC.BK", "TOP.BK", "DELTA.BK", "OSP.BK",
        "HANA.BK", "BH.BK", "CPAXT.BK", "SPRC.BK", "BEM.BK",
        "BTS.BK", "TISCO.BK", "COM7.BK", "KCE.BK", "JMT.BK",
        "SAWAD.BK", "GLOBAL.BK", "CRC.BK", "CBG.BK", "TIDLOR.BK",
    ],
    "cn": [
        # Hong Kong-listed China tech and EV names
        "0700.HK",  # Tencent
        "9988.HK",  # Alibaba
        "3690.HK",  # Meituan
        "1810.HK",  # Xiaomi
        "9618.HK",  # JD.com
        "9888.HK",  # Baidu
        "9999.HK",  # NetEase
        "1024.HK",  # Kuaishou
        "0981.HK",  # SMIC
        "1211.HK",  # BYD
        "2015.HK",  # Li Auto
        "9868.HK",  # XPeng
        "9866.HK",  # NIO
        "2318.HK",  # Ping An Insurance
        "0941.HK",  # China Mobile
        "1398.HK",  # ICBC
        "3988.HK",  # Bank of China
        "0883.HK",  # CNOOC
        # Mainland A-shares
        "600519.SS",  # Kweichow Moutai
        "600036.SS",  # China Merchants Bank
        "601318.SS",  # Ping An Insurance
        "300750.SZ",  # CATL
        "002594.SZ",  # BYD
        "601857.SS",  # PetroChina
        "600941.SS",  # China Mobile
        "601398.SS",  # ICBC
        "600900.SS",  # China Yangtze Power
        "601012.SS",  # LONGi Green Energy
        "002415.SZ",  # Hikvision
        "600030.SS",  # CITIC Securities
        "601088.SS",  # China Shenhua Energy
        "000858.SZ",  # Wuliangye
        "600309.SS",  # Wanhua Chemical
    ],
    "gold": [
        "XAUUSD=X",  # Gold spot quoted in USD
        "GC=F",  # COMEX gold futures
        "GLD",  # SPDR Gold Shares ETF
        "IAU",  # iShares Gold Trust
    ],
    "crypto": [
        "BTC-USD",  # Bitcoin
        "ETH-USD",  # Ethereum
        "SOL-USD",  # Solana
        "BNB-USD",  # BNB
        "XRP-USD",  # XRP
        "ADA-USD",  # Cardano
        "DOGE-USD",  # Dogecoin
        "AVAX-USD",  # Avalanche
        "LINK-USD",  # Chainlink
        "LTC-USD",  # Litecoin
    ],
}

MARKET_THRESHOLDS = {
    "us": {"min_change_pct": 1.2, "min_vol_ratio": 1.1},
    "th": {"min_change_pct": 0.8, "min_vol_ratio": 1.0},
    "cn": {"min_change_pct": 0.8, "min_vol_ratio": 1.0},
    "gold": {"min_change_pct": 0.15, "min_vol_ratio": 0.0},
    "crypto": {"min_change_pct": 0.8, "min_vol_ratio": 0.0},
}

TOP_N = 12
MAX_SCAN_WORKERS = 3
MARKET_SCAN_TIMEOUT_SECONDS = 30
MAX_DIAGNOSTIC_ERRORS = 5

logger = logging.getLogger(__name__)
_LAST_SCAN_DIAGNOSTICS: dict[str, dict] = {}


def _momentum_rank(summary: dict) -> int:
    """Score 1-5 for short-term momentum trading potential."""
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

    # Convert 0-10 to 1-5
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


def _convert_crypto_summary_to_thb(summary: dict) -> dict:
    rate = get_usd_thb_rate()
    setup = summary["trade_setup"]
    converted_setup = {
        **setup,
        "entry": round(setup["entry"] * rate, 2),
        "target": round(setup["target"] * rate, 2),
        "stop_loss": round(setup["stop_loss"] * rate, 2),
    }
    return {
        **summary,
        "price": round(summary["price"] * rate, 2),
        "change": round(summary["change"] * rate, 2),
        "trade_setup": converted_setup,
        "currency": "THB",
        "fx_rate": round(rate, 4),
    }


def _build_stock_summary(symbol: str, market: str) -> dict | None:
    thresholds = MARKET_THRESHOLDS.get(market, MARKET_THRESHOLDS["us"])
    quote = get_quote(symbol)
    avg_vol = quote.get("avg_volume", 1) or 1
    volume_ratio = 1.0 if market == "gold" and quote["volume"] <= 0 else quote["volume"] / avg_vol

    if (
        abs(quote["change_pct"]) < thresholds["min_change_pct"]
        and volume_ratio < thresholds["min_vol_ratio"]
    ):
        return None

    ta = analyze(symbol)
    if not ta:
        return None

    if settings.screener_include_news:
        news, news_sentiment, news_score = get_news_with_sentiment(symbol)
    else:
        news, news_sentiment, news_score = [], "neutral", 50.0
    setup_quote = quote
    if market == "gold" and quote["volume"] <= 0:
        setup_quote = {**quote, "volume": 1, "avg_volume": 1}
    setup = calculate_trade_setup(ta, setup_quote, news_score, news_sentiment)

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
    if market == "crypto":
        summary = _convert_crypto_summary_to_thb(summary)
    summary["momentum_rank"] = _momentum_rank(summary)
    return summary


def get_last_screener_diagnostics(market: str | None = None) -> dict:
    if market:
        return _LAST_SCAN_DIAGNOSTICS.get(market, {})
    return dict(_LAST_SCAN_DIAGNOSTICS)


def get_screener_results(market: str = "us") -> list[dict]:
    cache_key = f"screener:{market}:today"
    cached = _cache.get(cache_key, settings.screener_cache_ttl_seconds)
    if cached:
        return cached

    watchlist = MARKET_WATCHLISTS.get(market, MARKET_WATCHLISTS["us"])
    results = []
    failures = []
    failure_count = 0
    completed = 0
    workers = min(MAX_SCAN_WORKERS, len(watchlist))
    executor = ThreadPoolExecutor(max_workers=workers)
    futures = {
        executor.submit(_build_stock_summary, symbol, market): symbol
        for symbol in watchlist
    }
    try:
        for future in as_completed(futures, timeout=MARKET_SCAN_TIMEOUT_SECONDS):
            symbol = futures[future]
            completed += 1
            try:
                summary = future.result()
            except Exception as exc:
                failure_count += 1
                if len(failures) < MAX_DIAGNOSTIC_ERRORS:
                    failures.append({"symbol": symbol, "error": str(exc)})
                continue
            if summary:
                results.append(summary)
    except TimeoutError:
        logger.warning("Screener scan timed out for %s after %s seconds", market, MARKET_SCAN_TIMEOUT_SECONDS)
    finally:
        executor.shutdown(wait=True, cancel_futures=True)

    results.sort(key=_interest_score, reverse=True)
    top = results[:TOP_N]
    _LAST_SCAN_DIAGNOSTICS[market] = {
        "watchlist_count": len(watchlist),
        "completed_count": completed,
        "candidate_count": len(results),
        "returned_count": len(top),
        "failure_count": len(watchlist) - completed + failure_count,
        "sample_errors": failures,
    }
    if not top and failures:
        logger.warning("Screener returned no %s results; sample errors: %s", market, failures)
    _cache.set(cache_key, top)
    return top
