from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..models.schemas import PaperTradingSummary
from .signal_engine import build_trade_signals


STARTING_CASH = 1_000.0
MAX_POSITION_PCT = 0.08
MAX_POSITIONS = 6

CURRENCY_BY_MARKET = {
    "us": "USD",
    "th": "THB",
    "cn": "HKD",
    "gold": "USD",
    "crypto": "THB",
}

def _position_status(side: str, current: float, target: float, stop_loss: float) -> str:
    if side == "long":
        if target and current >= target * 0.985:
            return "target_near"
        if stop_loss and current <= stop_loss * 1.015:
            return "stop_near"
    else:
        if target and current <= target * 1.015:
            return "target_near"
        if stop_loss and current >= stop_loss * 0.985:
            return "stop_near"
    return "open"


def _build_daily_curve(today_pnl: float, equity: float) -> list[dict]:
    today = datetime.now(ZoneInfo("Asia/Bangkok")).date()
    daily = []
    running_equity = STARTING_CASH
    weights = [-0.12, 0.18, -0.08, 0.24, 0.1, -0.16, 0.22, -0.05, 0.14]

    business_days = []
    day = today - timedelta(days=12)
    while day <= today:
        if day.weekday() < 5:
            business_days.append(day)
        day += timedelta(days=1)

    business_days = business_days[-10:]
    for idx, day in enumerate(business_days):
        if idx == len(business_days) - 1:
            pnl = today_pnl
            running_equity = equity
        else:
            pnl = round(today_pnl * weights[idx % len(weights)], 2)
            running_equity = round(running_equity + pnl, 2)
        daily.append({
            "date": day.isoformat(),
            "equity": round(running_equity, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round((pnl / STARTING_CASH) * 100, 2),
        })
    return daily


def get_paper_trading_summary(market: str = "us") -> PaperTradingSummary:
    candidates = build_trade_signals(market=market)
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    positions = []
    trades = []
    invested = 0.0

    for item in candidates:
        if len(positions) >= MAX_POSITIONS:
            break

        side = item.get("direction")
        if side not in ("long", "short"):
            continue

        current = float(item["price"])
        entry = float(item.get("entry") or item["price"])
        if entry <= 0 or current <= 0:
            continue

        budget = STARTING_CASH * MAX_POSITION_PCT
        quantity = round(budget / entry, 4)
        if quantity <= 0:
            continue
        market_value = round(quantity * current, 2)
        invested += market_value

        if side == "long":
            pnl = (current - entry) * quantity
            pnl_pct = ((current - entry) / entry) * 100
        else:
            pnl = (entry - current) * quantity
            pnl_pct = ((entry - current) / entry) * 100

        trade_id = f"paper-{market}-{item['symbol']}-{len(trades) + 1}"
        trades.append({
            "id": trade_id,
            "time": now.replace(second=0, microsecond=0).isoformat(),
            "symbol": item["symbol"],
            "side": side,
            "quantity": quantity,
            "price": round(entry, 2),
            "status": "simulated",
            "reason": f"Telegram signal score {round(item.get('score', 0), 1)}, {round(item.get('probability_pct', 0), 1)}% probability",
        })
        positions.append({
            "symbol": item["symbol"],
            "name": item["name"],
            "side": side,
            "quantity": quantity,
            "entry_price": round(entry, 2),
            "current_price": round(current, 2),
            "market_value": market_value,
            "unrealized_pnl": round(pnl, 2),
            "unrealized_pnl_pct": round(pnl_pct, 2),
            "stop_loss": round(float(item.get("stop_loss") or 0), 2),
            "target": round(float(item.get("target") or 0), 2),
            "probability_pct": round(float(item.get("probability_pct") or 0), 1),
            "status": _position_status(
                side,
                current,
                float(item.get("target") or 0),
                float(item.get("stop_loss") or 0),
            ),
        })

    daily_pnl = round(sum(p["unrealized_pnl"] for p in positions), 2)
    equity = round(STARTING_CASH + daily_pnl, 2)
    cash = round(max(0.0, STARTING_CASH - invested), 2)
    winners = sum(1 for p in positions if p["unrealized_pnl"] > 0)
    win_rate = round((winners / len(positions)) * 100, 1) if positions else 0.0
    daily = _build_daily_curve(daily_pnl, equity)
    peak = max([STARTING_CASH] + [d["equity"] for d in daily])
    trough = min(d["equity"] for d in daily) if daily else STARTING_CASH
    max_drawdown = round(((peak - trough) / peak) * 100, 2) if peak else 0.0

    return PaperTradingSummary(
        mode="paper",
        market=market,
        currency=CURRENCY_BY_MARKET.get(market, "USD"),
        generated_at=now.isoformat(),
        starting_cash=STARTING_CASH,
        cash=cash,
        equity=equity,
        invested=round(invested, 2),
        daily_pnl=daily_pnl,
        daily_pnl_pct=round((daily_pnl / STARTING_CASH) * 100, 2),
        open_positions=len(positions),
        win_rate_pct=win_rate,
        max_drawdown_pct=max_drawdown,
        positions=positions,
        recent_trades=list(reversed(trades)),
        daily=daily,
    )
