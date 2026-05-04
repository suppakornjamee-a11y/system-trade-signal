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
    current_price = ta.get("current_price", quote["price"])
    support = ta["support"]
    resistance = ta["resistance"]
    atr = ta.get("atr") or (current_price * 0.02)
    trend = ta.get("trend", "neutral")

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

    # Entry / target / stop loss
    if direction == "long":
        entry = round(min(current_price, support * 1.005), 2)
        stop_loss = round(support - atr * 0.5, 2)
        target = round(resistance, 2)
    else:
        entry = round(max(current_price, resistance * 0.995), 2)
        stop_loss = round(resistance + atr * 0.5, 2)
        target = round(support, 2)

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
        "target": target,
        "stop_loss": stop_loss,
        "risk_reward": risk_reward,
        "probability_pct": prob,
        "tech_score": round(tech, 1),
        "news_score": round(news_score, 1),
        "volume_score": round(vol, 1),
    }
