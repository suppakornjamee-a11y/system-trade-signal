from fastapi import APIRouter, HTTPException, Query
from ..services.stock_service import get_quote, get_candles
from ..services.technical_analysis import analyze
from ..services.news_service import get_news_with_sentiment
from ..services.probability_engine import calculate_trade_setup

router = APIRouter()


@router.get("/{symbol}")
def stock_detail(symbol: str):
    symbol = symbol.upper()
    try:
        quote = get_quote(symbol)
        ta = analyze(symbol)
        if not ta:
            raise HTTPException(status_code=404, detail="Insufficient data")

        news, news_sentiment, news_score = get_news_with_sentiment(symbol)
        setup = calculate_trade_setup(ta, quote, news_score, news_sentiment)
        candles = get_candles(symbol, period="1d", interval="5m")

        avg_vol = quote.get("avg_volume", 1) or 1

        return {
            "symbol": symbol,
            "name": quote["name"],
            "price": quote["price"],
            "change": quote["change"],
            "change_pct": quote["change_pct"],
            "volume": quote["volume"],
            "avg_volume": avg_vol,
            "volume_ratio": round(quote["volume"] / avg_vol, 2),
            "market_cap": quote.get("market_cap"),
            "technical": ta,
            "trade_setup": setup,
            "news": news,
            "candles": candles,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/candles")
def stock_candles(
    symbol: str,
    period: str = Query("1d", pattern="^(1d|5d|1mo|3mo)$"),
    interval: str = Query("5m", pattern="^(1m|5m|15m|30m|1h|1d)$"),
):
    symbol = symbol.upper()
    try:
        return get_candles(symbol, period=period, interval=interval)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/quote")
def stock_quote(symbol: str):
    symbol = symbol.upper()
    try:
        return get_quote(symbol)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
