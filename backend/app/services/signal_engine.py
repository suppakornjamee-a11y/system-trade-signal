import html
import time

from .. import cache as _cache
from ..config import settings
from .screener_service import get_screener_results


def _direction_label(direction: str) -> str:
    return "สัญญาณซื้อ" if direction == "long" else "สัญญาณขาย/ออก"


def _entry_label(direction: str) -> str:
    return "โซนซื้อ" if direction == "long" else "โซนขาย/ออก"


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


def _score_signal(summary: dict) -> float:
    setup = summary["trade_setup"]
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
    return (
        score >= settings.signal_min_score
        and setup["risk_reward"] >= settings.signal_min_risk_reward
        and summary["volume_ratio"] >= 1.0
        and setup["direction"] in ("long", "short")
    )


def build_trade_signals(market: str = "us") -> list[dict]:
    signals = []
    for summary in get_screener_results(market=market):
        score = _score_signal(summary)
        if not _is_actionable(summary, score):
            continue

        setup = summary["trade_setup"]
        signals.append({
            "symbol": summary["symbol"],
            "name": summary["name"],
            "market": market,
            "direction": setup["direction"],
            "signal": _direction_label(setup["direction"]),
            "score": score,
            "price": summary["price"],
            "change_pct": summary["change_pct"],
            "volume_ratio": summary["volume_ratio"],
            "entry": setup["entry"],
            "target": setup["target"],
            "stop_loss": setup["stop_loss"],
            "risk_reward": setup["risk_reward"],
            "probability_pct": setup["probability_pct"],
            "reasons": _signal_reasons(summary),
            "created_at": int(time.time()),
        })

    signals.sort(key=lambda s: (s["score"], s["risk_reward"]), reverse=True)
    return signals


def should_send_signal(signal: dict) -> bool:
    key = f"signal:last_sent:{signal['symbol']}:{signal['direction']}"
    return _cache.get(key, settings.signal_cooldown_minutes * 60) is None


def mark_signal_sent(signal: dict) -> None:
    key = f"signal:last_sent:{signal['symbol']}:{signal['direction']}"
    _cache.set(key, int(time.time()))


def format_signal_message(signal: dict) -> str:
    reasons = "\n".join(f"- {html.escape(reason)}" for reason in signal["reasons"])

    return "\n".join([
        f"<b>{html.escape(signal['signal'])}</b>",
        f"<b>{html.escape(signal['symbol'])}</b> - {html.escape(signal['name'])}",
        f"คะแนน: <b>{signal['score']:.1f}</b> | โอกาส: {signal['probability_pct']:.1f}%",
        html.escape(_action_note(signal["direction"])),
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
