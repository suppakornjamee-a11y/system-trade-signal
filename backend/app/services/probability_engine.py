import math


def _round_price(value: float) -> float:
    return round(float(value), 4 if abs(value) < 1 else 2)


def _pct_distance(a: float, b: float) -> float:
    return abs(a - b) / b * 100 if b else 100.0


def _tech_score(ta: dict, direction: str) -> float:
    """Returns 0-100 technical score for the given direction (long/short)."""
    score = 50.0

    rsi = ta.get("rsi")
    if rsi is not None:
        if direction == "long":
            if rsi < 30:
                score += 25
            elif rsi < 45:
                score += 10
            elif rsi > 70:
                score -= 20
            elif rsi > 60:
                score -= 5
        else:  # short
            if rsi > 70:
                score += 25
            elif rsi > 55:
                score += 10
            elif rsi < 30:
                score -= 20
            elif rsi < 40:
                score -= 5

    macd = ta.get("macd")
    macd_signal = ta.get("macd_signal")
    if macd is not None and macd_signal is not None:
        if direction == "long":
            score += 15 if macd > macd_signal else -15
        else:
            score += 15 if macd < macd_signal else -15

    trend = ta.get("trend", "neutral")
    if direction == "long":
        score += 15 if trend == "bullish" else (-10 if trend == "bearish" else 0)
    else:
        score += 15 if trend == "bearish" else (-10 if trend == "bullish" else 0)

    return max(0.0, min(100.0, score))


def _volume_score(volume_ratio: float) -> float:
    if volume_ratio >= 3.0:
        return 100.0
    if volume_ratio >= 2.0:
        return 85.0
    if volume_ratio >= 1.5:
        return 70.0
    if volume_ratio >= 1.2:
        return 55.0
    if volume_ratio >= 0.8:
        return 40.0
    return 25.0


def calculate_trade_setup(
    ta: dict,
    quote: dict,
    news_score: float,
    news_sentiment: str,
) -> dict:
    current_price = float(quote.get("price") or ta.get("current_price") or 0)
    support = ta["support"]
    resistance = ta["resistance"]
    atr = ta.get("atr") or (current_price * 0.02)
    trend = ta.get("trend", "neutral")
    if not current_price or not math.isfinite(current_price):
        current_price = float(ta.get("current_price") or quote["price"])
    if not atr or not math.isfinite(float(atr)) or atr <= 0:
        atr = current_price * 0.02

    # Determine direction
    if news_sentiment == "bullish" and trend in ("bullish", "neutral"):
        direction = "long"
    elif news_sentiment == "bearish" and trend in ("bearish", "neutral"):
        direction = "short"
    elif trend == "bullish":
        direction = "long"
    elif trend == "bearish":
        direction = "short"
    else:
        direction = "long"  # default

    # Entry / target / stop loss.
    # The setup is designed for alerts, so the primary entry stays near the
    # current tradable price. Wider support/resistance levels are used as
    # context, not as a far-away entry that cannot be acted on when notified.
    max_risk = current_price * 0.035
    min_risk = current_price * 0.006
    risk_distance = min(max(atr * 0.9, min_risk), max_risk)
    entry_band = min(max(atr * 0.25, current_price * 0.003), current_price * 0.012)

    if direction == "long":
        pullback_entry = support * 1.005
        entry = current_price if _pct_distance(current_price, pullback_entry) > 1.0 else pullback_entry
        entry = min(entry, current_price)
        technical_stop = support - atr * 0.25
        stop_loss = max(technical_stop, entry - risk_distance)
        nearest_target = resistance if resistance > entry else entry + atr * 1.5
        target = min(nearest_target, entry + atr * 2.0)
        min_target = entry + max(abs(entry - stop_loss) * 1.15, atr * 0.75)
        target = max(target, min_target)
        action = "ready" if _pct_distance(current_price, entry) <= 0.75 else "wait_pullback"
        entry_zone_low = entry - entry_band
        entry_zone_high = entry + entry_band
    else:
        bounce_entry = resistance * 0.995
        entry = current_price if _pct_distance(current_price, bounce_entry) > 1.0 else bounce_entry
        entry = max(entry, current_price)
        technical_stop = resistance + atr * 0.25
        stop_loss = min(technical_stop, entry + risk_distance)
        nearest_target = support if support < entry else entry - atr * 1.5
        target = max(nearest_target, entry - atr * 2.0)
        min_target = entry - max(abs(stop_loss - entry) * 1.15, atr * 0.75)
        target = min(target, min_target)
        action = "ready" if _pct_distance(current_price, entry) <= 0.75 else "wait_bounce"
        entry_zone_low = entry - entry_band
        entry_zone_high = entry + entry_band

    entry = _round_price(entry)
    target = _round_price(target)
    stop_loss = _round_price(stop_loss)
    entry_zone_low = _round_price(entry_zone_low)
    entry_zone_high = _round_price(entry_zone_high)

    # Risk / reward
    risk = abs(entry - stop_loss)
    reward = abs(target - entry)
    risk_reward = round(reward / risk, 2) if risk > 0 else 0.0

    # Scores
    avg_vol = quote.get("avg_volume", 1) or 1
    volume_ratio = quote["volume"] / avg_vol
    tech = _tech_score(ta, direction)
    vol = _volume_score(volume_ratio)

    # Final probability
    rr_score = min(risk_reward / 3.0 * 100, 100.0)
    prob = (tech * 0.40 + news_score * 0.35 + vol * 0.15 + rr_score * 0.10)
    prob = round(max(20.0, min(85.0, prob)), 1)

    return {
        "direction": direction,
        "entry": entry,
        "entry_zone_low": entry_zone_low,
        "entry_zone_high": entry_zone_high,
        "target": target,
        "stop_loss": stop_loss,
        "risk_reward": risk_reward,
        "probability_pct": prob,
        "tech_score": round(tech, 1),
        "news_score": round(news_score, 1),
        "volume_score": round(vol, 1),
        "action": action,
        "entry_distance_pct": round(_pct_distance(current_price, entry), 2),
        "target_room_pct": round(
            ((target - current_price) / current_price * 100)
            if direction == "long"
            else ((current_price - target) / current_price * 100),
            2,
        ),
    }
