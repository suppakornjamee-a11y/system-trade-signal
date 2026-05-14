import html
import math
import time

from .. import cache as _cache
from ..config import settings
from .stock_service import get_history
from .screener_service import get_screener_results


def _direction_label(direction: str) -> str:
    return "สัญญาณซื้อ" if direction == "long" else "สัญญาณขาย/ออก"


def _market_label(market: str) -> str:
    labels = {
        "us": "หุ้นสหรัฐ",
        "th": "หุ้นไทย",
        "cn": "หุ้นจีน/HK",
        "gold": "ทองคำ",
        "crypto": "Crypto",
    }
    return labels.get(market, market.upper())


def _entry_label(direction: str) -> str:
    return "จุดเข้า Long/โซนซื้อ" if direction == "long" else "จุดเข้า Short/โซนขาย"


def _target_label(direction: str) -> str:
    return "เป้าขายทำกำไร" if direction == "long" else "เป้าลงถัดไป"


def _stop_label(direction: str) -> str:
    return "จุดตัดขาดทุน" if direction == "long" else "จุดยกเลิกสัญญาณขาย"


def _action_note(direction: str) -> str:
    if direction == "long":
        return "แผนตอนนี้: เข้า Long ได้เฉพาะเมื่อราคายังอยู่ในโซนเข้า ถ้าราคาหนีโซนแล้วให้ข้าม ไม่ไล่ซื้อ"
    return "แผนตอนนี้: ใช้เป็นจุด Short/ลดพอร์ตเฉพาะเมื่อราคายังอยู่ในโซนขาย ถ้าราคาหลุดโซนแล้วให้รอใหม่"


def _gold_scalp_note(direction: str) -> str:
    if direction == "long":
        return "แผนทองเร็ว: เข้า Long ได้เฉพาะในโซนนี้ เน้นกินสั้น ถ้าหลุด stop หรือไม่ไปใน 2-3 แท่ง 5 นาทีให้ปิด/ลดทันที"
    return "แผนทองเร็ว: เข้า Short ได้เฉพาะในโซนนี้ เน้นกินสั้น ถ้าทะลุ stop หรือไม่ลงใน 2-3 แท่ง 5 นาทีให้ปิด/ลดทันที"


def _action_label(signal: dict) -> str:
    action = signal.get("action")
    if action == "ready":
        return "เข้าได้ตอนนี้"
    if action == "wait_bounce":
        return "รอเด้งเข้าโซน"
    return "รอย่อเข้าโซน"


def _execution_line(signal: dict, currency: str) -> str:
    direction = signal["direction"]
    entry_zone_low = signal.get("entry_zone_low", signal["entry"])
    entry_zone_high = signal.get("entry_zone_high", signal["entry"])
    if direction == "long":
        return (
            f"ซื้อในโซน <b>{_format_price(entry_zone_low, currency)} - "
            f"{_format_price(entry_zone_high, currency)}</b>; "
            f"หลุด {_format_price(signal['stop_loss'], currency)} ตัดทันที"
        )
    return (
        f"Short/ลดพอร์ตในโซน <b>{_format_price(entry_zone_low, currency)} - "
        f"{_format_price(entry_zone_high, currency)}</b>; "
        f"ทะลุ {_format_price(signal['stop_loss'], currency)} ยกเลิกแผน"
    )


def _signal_reasons(summary: dict) -> list[str]:
    setup = summary["trade_setup"]
    reasons = []

    if setup["probability_pct"] >= 75:
        reasons.append(f"โอกาสตามแผนสูง {setup['probability_pct']:.1f}%")
    if summary["volume_ratio"] >= 1.5:
        reasons.append(f"วอลุ่มสูงกว่าปกติ {summary['volume_ratio']:.2f} เท่า")
    if abs(summary["change_pct"]) >= 2:
        reasons.append(f"ราคาเคลื่อนไหวแรง {summary['change_pct']:+.2f}%")
    if setup["risk_reward"] >= 1.5:
        reasons.append(f"ผลตอบแทนต่อความเสี่ยง {setup['risk_reward']:.2f}")
    if summary.get("news_sentiment") != "neutral":
        reasons.append(f"ข่าวเอนเอียงทาง {summary['news_sentiment']}")
    if summary.get("momentum_rank", 0) >= 4:
        reasons.append(f"แรงเหวี่ยง {summary['momentum_rank']}/5")

    return reasons or ["เข้าเงื่อนไขเทคนิคสำหรับเล่นสั้น"]


def _gold_scalp_signal() -> dict | None:
    if not settings.gold_scalp_enabled:
        return None

    symbol = ""
    name = "Gold Spot"
    df = None
    for candidate, candidate_name in (
        ("GC=F", "Gold Futures"),
        ("MGC=F", "Micro Gold Futures"),
    ):
        try:
            candidate_df = get_history(candidate, period="1d", interval="5m")
        except Exception:
            continue
        if not candidate_df.empty:
            symbol = candidate
            name = candidate_name
            df = candidate_df
            break

    if df is None:
        return None

    if df.empty or len(df) < 35:
        return None

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"] if "volume" in df else None

    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, math.nan)
    rsi = 100 - (100 / (1 + rs))

    prev_close = close.shift(1)
    true_range = max(
        float((high.iloc[-14:] - low.iloc[-14:]).mean()),
        float((high.iloc[-14:] - prev_close.iloc[-14:]).abs().mean()),
        float((low.iloc[-14:] - prev_close.iloc[-14:]).abs().mean()),
    )
    atr = true_range if math.isfinite(true_range) and true_range > 0 else float(close.iloc[-1]) * 0.001

    price = float(close.iloc[-1])
    previous_price = float(close.iloc[-2])
    change = price - previous_price
    change_pct = (change / previous_price) * 100 if previous_price else 0.0
    last_rsi = float(rsi.iloc[-1]) if math.isfinite(float(rsi.iloc[-1])) else 50.0
    last_ema9 = float(ema9.iloc[-1])
    last_ema21 = float(ema21.iloc[-1])
    last_ema50 = float(ema50.iloc[-1])
    prior_ema9 = float(ema9.iloc[-2])
    prior_ema21 = float(ema21.iloc[-2])
    momentum = price - float(close.iloc[-4])

    long_setup = (
        last_ema9 > last_ema21 >= last_ema50
        and price >= last_ema9
        and momentum > 0
        and 40 <= last_rsi <= 80
        and price <= last_ema9 + atr * 0.8
    )
    short_setup = (
        last_ema9 < last_ema21 <= last_ema50
        and price <= last_ema9
        and momentum < 0
        and 20 <= last_rsi <= 60
        and price >= last_ema9 - atr * 0.8
    )
    fresh_cross = abs((last_ema9 - last_ema21) - (prior_ema9 - prior_ema21)) > atr * 0.03

    if not long_setup and not short_setup:
        return None

    direction = "long" if long_setup else "short"
    risk_usd = min(max(atr * 0.75, 1.5), settings.gold_scalp_max_stop_usd)
    reward_usd = max(risk_usd * 1.2, settings.gold_scalp_min_target_usd)
    entry_band = min(max(atr * 0.18, 0.7), 2.0)

    if direction == "long":
        stop_loss = price - risk_usd
        target = price + reward_usd
    else:
        stop_loss = price + risk_usd
        target = price - reward_usd

    trend_score = 22 if fresh_cross else 14
    rsi_score = 18 if (direction == "long" and last_rsi < 66) or (direction == "short" and last_rsi > 34) else 10
    momentum_score = min(abs(momentum) / max(atr, 0.01) * 18, 18)
    score = round(min(88.0, 42 + trend_score + rsi_score + momentum_score), 1)
    if score < settings.gold_scalp_min_score:
        return None

    volume_value = int(volume.iloc[-1]) if volume is not None and math.isfinite(float(volume.iloc[-1])) else 0

    return {
        "symbol": symbol,
        "name": name,
        "market": "gold",
        "direction": direction,
        "signal": "สัญญาณทองเร็ว",
        "score": score,
        "price": round(price, 2),
        "change_pct": round(change_pct, 2),
        "volume_ratio": 1.0,
        "entry": round(price, 2),
        "entry_zone_low": round(price - entry_band, 2),
        "entry_zone_high": round(price + entry_band, 2),
        "target": round(target, 2),
        "stop_loss": round(stop_loss, 2),
        "risk_reward": round(reward_usd / risk_usd, 2) if risk_usd else 0.0,
        "probability_pct": score,
        "entry_distance_pct": 0.0,
        "target_room_pct": round(abs(target - price) / price * 100, 2) if price else 0.0,
        "reasons": [
            f"กราฟ 5 นาที EMA9 {'อยู่เหนือ' if direction == 'long' else 'อยู่ใต้'} EMA21",
            f"RSI {last_rsi:.1f} ยังพอมีพื้นที่สำหรับ scalp",
            f"ATR 5m ประมาณ {atr:.2f} ใช้ตั้ง stop/target สั้น",
        ],
        "created_at": int(time.time()),
        "is_snack_trade": False,
        "currency": "USD",
        "action": "ready",
        "style": "gold_scalp",
        "timeframe": "5m",
        "volume": volume_value,
    }


def _snack_trade_note(direction: str) -> str:
    if direction == "long":
        return "หมายเหตุค่าขนม: ตัวนี้ยังไม่ใช่สัญญาณหลัก แต่ราคายังอยู่ใกล้โซนเข้า เล่นเบา ๆ ลดไซซ์ และห้ามไล่ถ้าราคาเริ่มหนีโซน"
    return "หมายเหตุค่าขนม: ตัวนี้ยังไม่ใช่สัญญาณหลัก แต่ราคาอยู่ใกล้โซนขาย/ลดพอร์ต ใช้เป็นจุดระวัง ไม่ใช่จุดใส่สุด"


def _is_finite_number(value) -> bool:
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def _has_valid_trade_numbers(summary: dict) -> bool:
    setup = summary["trade_setup"]
    return all(
        _is_finite_number(value)
        for value in (
            summary.get("price"),
            summary.get("change_pct"),
            summary.get("volume_ratio"),
            setup.get("entry"),
            setup.get("target"),
            setup.get("stop_loss"),
            setup.get("entry_zone_low", setup.get("entry")),
            setup.get("entry_zone_high", setup.get("entry")),
            setup.get("risk_reward"),
            setup.get("probability_pct"),
            setup.get("tech_score"),
            setup.get("volume_score"),
        )
    )


def _score_signal(summary: dict) -> float:
    setup = summary["trade_setup"]
    if not _has_valid_trade_numbers(summary):
        return 0.0

    probability = setup["probability_pct"]
    rr_score = min(setup["risk_reward"] / 3 * 100, 100)
    momentum_score = min(abs(summary["change_pct"]) / 5 * 100, 100)
    rank_score = summary.get("momentum_rank", 1) / 5 * 100

    score = (
        probability * 0.45
        + setup["tech_score"] * 0.20
        + setup["volume_score"] * 0.15
        + rr_score * 0.10
        + momentum_score * 0.05
        + rank_score * 0.05
    )
    return round(max(0, min(100, score)), 1)


def _trade_window(summary: dict) -> dict:
    setup = summary["trade_setup"]
    price = float(summary["price"])
    entry = float(setup["entry"])
    target = float(setup["target"])
    direction = setup["direction"]
    entry_distance_pct = abs(price - entry) / entry * 100 if entry else 100.0

    if direction == "long":
        target_room_pct = (target - price) / price * 100 if price else -100.0
    else:
        target_room_pct = (price - target) / price * 100 if price else -100.0

    return {
        "entry_distance_pct": entry_distance_pct,
        "target_room_pct": target_room_pct,
    }


def _is_trade_ready(
    summary: dict,
    max_entry_distance_pct: float,
    min_target_room_pct: float,
) -> bool:
    if not _has_valid_trade_numbers(summary):
        return False

    window = _trade_window(summary)
    setup = summary["trade_setup"]
    return (
        setup.get("action", "ready") == "ready"
        and
        window["entry_distance_pct"] <= max_entry_distance_pct
        and window["target_room_pct"] >= min_target_room_pct
    )


def _is_actionable(summary: dict, score: float) -> bool:
    setup = summary["trade_setup"]
    market = summary.get("market")
    min_score = (
        60.0 if market == "th"
        else (62.0 if market in ("gold", "crypto") else settings.signal_min_score)
    )
    min_risk_reward = (
        1.0 if market in ("th", "crypto")
        else (1.1 if market == "gold" else settings.signal_min_risk_reward)
    )
    min_volume_ratio = 0.8 if market == "th" else (0.0 if market in ("gold", "crypto") else 1.0)
    max_entry_distance_pct = (
        0.35 if market == "gold"
        else (3.0 if market == "crypto" else settings.signal_max_entry_distance_pct)
    )
    min_target_room_pct = (
        0.2 if market == "gold"
        else (0.5 if market == "crypto" else settings.signal_min_target_room_pct)
    )

    return (
        _has_valid_trade_numbers(summary)
        and score >= min_score
        and setup["risk_reward"] >= min_risk_reward
        and summary["volume_ratio"] >= min_volume_ratio
        and setup["direction"] in ("long", "short")
        and _is_trade_ready(
            summary,
            max_entry_distance_pct,
            min_target_room_pct,
        )
    )


def _is_snack_trade(summary: dict, score: float) -> bool:
    setup = summary["trade_setup"]
    if not settings.snack_trade_enabled or not _has_valid_trade_numbers(summary):
        return False

    market = summary.get("market")
    min_score = (
        min(settings.snack_trade_min_score, 52.0)
        if market in ("th", "us")
        else settings.snack_trade_min_score
    )
    min_risk_reward = (
        min(settings.snack_trade_min_risk_reward, 0.8)
        if market == "th"
        else (0.9 if market == "us" else (0.8 if market == "crypto" else settings.snack_trade_min_risk_reward))
    )
    max_entry_distance_pct = (
        0.25 if market == "gold"
        else (
            2.0 if market == "crypto"
            else min(settings.snack_trade_max_entry_distance_pct, settings.signal_max_entry_distance_pct)
        )
    )
    min_target_room_pct = (
        0.2 if market == "gold"
        else (0.5 if market in ("crypto", "us") else settings.snack_trade_min_target_room_pct)
    )
    min_volume_ratio = (
        0.0 if market in ("gold", "crypto")
        else (0.3 if market == "us" else settings.snack_trade_min_volume_ratio)
    )

    return (
        score >= min_score
        and setup["risk_reward"] >= min_risk_reward
        and summary["volume_ratio"] >= min_volume_ratio
        and setup["direction"] in ("long", "short")
        and _is_trade_ready(
            summary,
            max_entry_distance_pct,
            min_target_room_pct,
        )
    )


def _build_signal(summary: dict, market: str, score: float, is_snack_trade: bool = False) -> dict:
    setup = summary["trade_setup"]
    window = _trade_window(summary)
    signal = {
        "symbol": summary["symbol"],
        "name": summary["name"],
        "market": market,
        "direction": setup["direction"],
        "signal": _direction_label(setup["direction"]),
        "score": float(score),
        "price": float(summary["price"]),
        "change_pct": float(summary["change_pct"]),
        "volume_ratio": float(summary["volume_ratio"]),
        "entry": float(setup["entry"]),
        "entry_zone_low": float(setup.get("entry_zone_low", setup["entry"])),
        "entry_zone_high": float(setup.get("entry_zone_high", setup["entry"])),
        "target": float(setup["target"]),
        "stop_loss": float(setup["stop_loss"]),
        "risk_reward": float(setup["risk_reward"]),
        "probability_pct": float(setup["probability_pct"]),
        "entry_distance_pct": round(window["entry_distance_pct"], 2),
        "target_room_pct": round(window["target_room_pct"], 2),
        "action": setup.get("action", "ready"),
        "reasons": _signal_reasons(summary),
        "created_at": int(time.time()),
        "is_snack_trade": is_snack_trade,
        "currency": summary.get("currency", "USD"),
        "fx_rate": summary.get("fx_rate"),
    }
    if is_snack_trade:
        signal["reasons"] = ["ค่าขนม: เป็นตัวสำรองในวันที่ไม่มีสัญญาณหลัก"] + signal["reasons"]
    return signal


def _format_price(value: float, currency: str) -> str:
    if currency == "THB":
        return f"{value:,.2f} THB"
    return f"{value:,.2f}"


def build_trade_signals(market: str = "us") -> list[dict]:
    if market == "gold":
        signal = _gold_scalp_signal()
        return [signal] if signal else []

    signals = []
    snack_candidates = []
    for summary in get_screener_results(market=market):
        score = _score_signal(summary)
        if _is_actionable(summary, score):
            signals.append(_build_signal(summary, market, score))
        elif _is_snack_trade(summary, score):
            snack_candidates.append(_build_signal(summary, market, score, is_snack_trade=True))

    signals.sort(key=lambda s: (s["score"], s["risk_reward"]), reverse=True)
    if not signals and snack_candidates:
        snack_candidates.sort(key=lambda s: (s["score"], s["risk_reward"]), reverse=True)
        signals = snack_candidates[:settings.snack_trade_max_per_market]
    return signals


def should_send_signal(signal: dict) -> bool:
    signal_type = signal.get("style") or ("snack" if signal.get("is_snack_trade") else "main")
    key = f"signal:last_sent:{signal['symbol']}:{signal['direction']}:{signal_type}"
    if signal_type == "gold_scalp":
        ttl_seconds = settings.gold_scalp_dedupe_ttl_minutes * 60
    elif signal.get("market") == "crypto":
        ttl_seconds = settings.crypto_signal_dedupe_ttl_minutes * 60
    elif signal.get("is_snack_trade"):
        ttl_seconds = settings.snack_signal_dedupe_ttl_minutes * 60
    else:
        ttl_seconds = settings.signal_dedupe_ttl_hours * 60 * 60
    return _cache.get(key, ttl_seconds) is None


def mark_signal_sent(signal: dict) -> None:
    signal_type = signal.get("style") or ("snack" if signal.get("is_snack_trade") else "main")
    key = f"signal:last_sent:{signal['symbol']}:{signal['direction']}:{signal_type}"
    _cache.set(key, int(time.time()))


def format_signal_message(signal: dict) -> str:
    reasons = "\n".join(f"- {html.escape(reason)}" for reason in signal["reasons"])
    snack_suffix = " (ค่าขนม)" if signal.get("is_snack_trade") else ""
    if signal.get("style") == "gold_scalp":
        action_note = _gold_scalp_note(signal["direction"])
    else:
        action_note = _snack_trade_note(signal["direction"]) if signal.get("is_snack_trade") else _action_note(signal["direction"])
    market_label = _market_label(signal.get("market", ""))
    currency = signal.get("currency", "USD")
    action_label = _action_label(signal)
    direction = "LONG" if signal["direction"] == "long" else ("SHORT" if signal.get("style") == "gold_scalp" else "SHORT/REDUCE")
    title = "ทองเร็ว" if signal.get("style") == "gold_scalp" else action_label

    return "\n".join([
        f"<b>{html.escape(title)}: {html.escape(direction)} {html.escape(signal['symbol'])}</b>{snack_suffix}",
        html.escape(signal["name"]),
        f"ตลาด: {html.escape(market_label)} | คะแนน: <b>{signal['score']:.1f}</b> | โอกาส: {signal['probability_pct']:.1f}%",
        *([f"Timeframe: {html.escape(signal['timeframe'])} | ถือสั้นตามแท่ง 5 นาที"] if signal.get("style") == "gold_scalp" else []),
        "",
        html.escape(action_note),
        _execution_line(signal, currency),
        "",
        f"ตอนนี้: {_format_price(signal['price'], currency)} ({signal['change_pct']:+.2f}%)",
        f"{_entry_label(signal['direction'])}: <b>{_format_price(signal['entry'], currency)}</b> | ห่าง {signal['entry_distance_pct']:.2f}%",
        f"{_target_label(signal['direction'])}: <b>{_format_price(signal['target'], currency)}</b> | เหลือ {signal['target_room_pct']:.2f}%",
        f"{_stop_label(signal['direction'])}: <b>{_format_price(signal['stop_loss'], currency)}</b>",
        f"Risk/Reward: <b>{signal['risk_reward']:.2f}</b>",
        "",
        "เหตุผล:",
        reasons,
    ])
