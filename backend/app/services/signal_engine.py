import html
import math
import time

from .. import cache as _cache
from ..config import settings
from .screener_service import get_screener_results


def _direction_label(direction: str) -> str:
    return "สัญญาณซื้อ" if direction == "long" else "สัญญาณขาย/ออก"


def _entry_label(direction: str) -> str:
    return "จุดเข้า Long/โซนซื้อ" if direction == "long" else "จุดเข้า Short/โซนขาย"


def _target_label(direction: str) -> str:
    return "เป้าขายทำกำไร" if direction == "long" else "เป้าลงถัดไป"


def _stop_label(direction: str) -> str:
    return "จุดตัดขาดทุน" if direction == "long" else "จุดยกเลิกสัญญาณขาย"


def _action_note(direction: str) -> str:
    if direction == "long":
        return "คำแนะนำ: รอราคาเข้าโซนและมีแรงยืนยันก่อนซื้อ ไม่ไล่ราคาสูงเกินแผน"
    return "คำแนะนำ: ถ้ามีหุ้นอยู่ให้ระวัง พิจารณาลดพอร์ต/ออกเมื่ออ่อนตัวตามสัญญาณ"


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


def _snack_trade_note(direction: str) -> str:
    if direction == "long":
        return "หมายเหตุค่าขนม: ตัวนี้ยังไม่ใช่สัญญาณหลัก เล่นเบา ๆ เท่านั้น ลดไซซ์ รอราคาเข้าโซน และห้ามไล่ถ้าราคาเลยแผน"
    return "หมายเหตุค่าขนม: ตัวนี้ยังไม่ใช่สัญญาณหลัก เล่นเบา ๆ เท่านั้น ลดไซซ์ และใช้เป็นจุดระวัง/ลดพอร์ต ไม่ใช่จุดใส่สุด"


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


def _is_actionable(summary: dict, score: float) -> bool:
    setup = summary["trade_setup"]
    market = summary.get("market")
    min_score = 60.0 if market == "th" else settings.signal_min_score
    min_risk_reward = 1.0 if market == "th" else settings.signal_min_risk_reward
    min_volume_ratio = 0.8 if market == "th" else 1.0

    return (
        _has_valid_trade_numbers(summary)
        and score >= min_score
        and setup["risk_reward"] >= min_risk_reward
        and summary["volume_ratio"] >= min_volume_ratio
        and setup["direction"] in ("long", "short")
    )


def _is_snack_trade(summary: dict, score: float) -> bool:
    setup = summary["trade_setup"]
    if not settings.snack_trade_enabled or not _has_valid_trade_numbers(summary):
        return False

    market = summary.get("market")
    min_score = min(settings.snack_trade_min_score, 55.0) if market == "th" else settings.snack_trade_min_score
    min_risk_reward = min(settings.snack_trade_min_risk_reward, 0.8) if market == "th" else settings.snack_trade_min_risk_reward
    price = float(summary["price"])
    entry = float(setup["entry"])
    target = float(setup["target"])
    entry_distance_pct = abs(price - entry) / entry * 100 if entry else 100
    if setup["direction"] == "long":
        target_room_pct = (target - price) / price * 100 if price else -100
    else:
        target_room_pct = (price - target) / price * 100 if price else -100

    return (
        score >= min_score
        and setup["risk_reward"] >= min_risk_reward
        and summary["volume_ratio"] >= settings.snack_trade_min_volume_ratio
        and entry_distance_pct <= settings.snack_trade_max_entry_distance_pct
        and target_room_pct >= settings.snack_trade_min_target_room_pct
        and setup["direction"] in ("long", "short")
    )


def _build_signal(summary: dict, market: str, score: float, is_snack_trade: bool = False) -> dict:
    setup = summary["trade_setup"]
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
        "target": float(setup["target"]),
        "stop_loss": float(setup["stop_loss"]),
        "risk_reward": float(setup["risk_reward"]),
        "probability_pct": float(setup["probability_pct"]),
        "reasons": _signal_reasons(summary),
        "created_at": int(time.time()),
        "is_snack_trade": is_snack_trade,
    }
    if is_snack_trade:
        signal["reasons"] = ["ค่าขนม: เป็นตัวสำรองในวันที่ไม่มีสัญญาณหลัก"] + signal["reasons"]
    return signal


def build_trade_signals(market: str = "us") -> list[dict]:
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
    signal_type = "snack" if signal.get("is_snack_trade") else "main"
    key = f"signal:last_sent:{signal['symbol']}:{signal['direction']}:{signal_type}"
    return _cache.get(key, settings.signal_cooldown_minutes * 60) is None


def mark_signal_sent(signal: dict) -> None:
    signal_type = "snack" if signal.get("is_snack_trade") else "main"
    key = f"signal:last_sent:{signal['symbol']}:{signal['direction']}:{signal_type}"
    _cache.set(key, int(time.time()))


def format_signal_message(signal: dict) -> str:
    reasons = "\n".join(f"- {html.escape(reason)}" for reason in signal["reasons"])
    snack_suffix = " (ค่าขนม)" if signal.get("is_snack_trade") else ""
    action_note = _snack_trade_note(signal["direction"]) if signal.get("is_snack_trade") else _action_note(signal["direction"])

    return "\n".join([
        f"<b>{html.escape(signal['signal'])}</b>",
        f"<b>{html.escape(signal['symbol'])}</b>{snack_suffix} - {html.escape(signal['name'])}",
        f"คะแนน: <b>{signal['score']:.1f}</b> | โอกาส: {signal['probability_pct']:.1f}%",
        html.escape(action_note),
        "",
        f"ราคาปัจจุบัน: {signal['price']:.2f} ({signal['change_pct']:+.2f}%)",
        f"{_entry_label(signal['direction'])}: <b>{signal['entry']:.2f}</b>",
        f"{_target_label(signal['direction'])}: <b>{signal['target']:.2f}</b>",
        f"{_stop_label(signal['direction'])}: <b>{signal['stop_loss']:.2f}</b>",
        f"Risk/Reward: {signal['risk_reward']:.2f}",
        "",
        "เหตุผล:",
        reasons,
    ])
