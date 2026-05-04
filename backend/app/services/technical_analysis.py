import numpy as np
import pandas as pd

from .stock_service import get_history


def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 20:
        return df

    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    df["ma20"] = df["close"].rolling(20).mean()
    df["ma50"] = df["close"].rolling(50).mean()
    bb_std = df["close"].rolling(20).std()
    df["bb_middle"] = df["ma20"]
    df["bb_upper"] = df["bb_middle"] + (bb_std * 2)
    df["bb_lower"] = df["bb_middle"] - (bb_std * 2)

    prev_close = df["close"].shift(1)
    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["atr"] = true_range.rolling(14).mean()

    return df


def _find_support_resistance(df: pd.DataFrame, current_price: float) -> tuple[float, float]:
    if len(df) < 5:
        return current_price * 0.97, current_price * 1.03

    highs = df["high"].values
    lows = df["low"].values
    supports, resistances = [], []

    for i in range(1, len(highs) - 1):
        if lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
            supports.append(lows[i])
        if highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
            resistances.append(highs[i])

    supports_below = sorted([s for s in supports if s < current_price], reverse=True)
    resistances_above = sorted([r for r in resistances if r > current_price])

    support = supports_below[0] if supports_below else current_price * 0.97
    resistance = resistances_above[0] if resistances_above else current_price * 1.03

    return round(support, 2), round(resistance, 2)


def analyze(symbol: str) -> dict:
    df = get_history(symbol, period="3mo", interval="1d")
    if df.empty:
        return {}

    df = _compute_indicators(df)
    last = df.iloc[-1]
    current_price = float(last["close"])
    support, resistance = _find_support_resistance(df, current_price)

    def safe(val):
        try:
            v = float(val)
            return round(v, 4) if not np.isnan(v) else None
        except Exception:
            return None

    rsi = safe(last.get("rsi"))
    macd = safe(last.get("macd"))
    macd_signal = safe(last.get("macd_signal"))
    ma20 = safe(last.get("ma20"))
    ma50 = safe(last.get("ma50"))
    atr = safe(last.get("atr"))

    # Determine trend
    if ma20 and ma50:
        trend = "bullish" if ma20 > ma50 and current_price > ma20 else (
            "bearish" if ma20 < ma50 and current_price < ma20 else "neutral"
        )
    elif ma20:
        trend = "bullish" if current_price > ma20 else "bearish"
    else:
        trend = "neutral"

    return {
        "rsi": rsi,
        "macd": macd,
        "macd_signal": macd_signal,
        "macd_hist": safe(last.get("macd_hist")),
        "ma20": ma20,
        "ma50": ma50,
        "bb_upper": safe(last.get("bb_upper")),
        "bb_lower": safe(last.get("bb_lower")),
        "atr": atr,
        "support": support,
        "resistance": resistance,
        "trend": trend,
        "current_price": current_price,
    }
