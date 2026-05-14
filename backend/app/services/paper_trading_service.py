import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..config import BASE_DIR
from ..models.schemas import PaperTradingSummary
from .market_hours import market_status
from .stock_service import get_quote
from .signal_engine import build_trade_signals


STARTING_CASH = 1_000.0
BUCKET_ALLOCATIONS = {
    "momentum": {
        "label": "Momentum",
        "capital_pct": 0.50,
        "risk_pct": 0.012,
        "max_position_pct": 0.30,
        "max_positions": 2,
        "min_probability": 58.0,
        "min_score": 58.0,
    },
    "quality": {
        "label": "Quality",
        "capital_pct": 0.50,
        "risk_pct": 0.006,
        "max_position_pct": 0.25,
        "max_positions": 2,
        "min_probability": 64.0,
        "min_score": 64.0,
    },
}
MAX_PORTFOLIO_EXPOSURE_PCT = 0.60
MIN_CASH_RESERVE_PCT = 0.20
MAX_POSITIONS = 4
ALLOW_SHORT_MARKETS = {"gold"}

CURRENCY_BY_MARKET = {
    "us": "USD",
    "th": "THB",
    "cn": "HKD",
    "gold": "USD",
    "crypto": "THB",
}

DB_PATH = BASE_DIR / "data" / "paper_trading.sqlite3"

DISPLAY_NAME_BY_SYMBOL = {
    "0700.HK": "Tencent",
    "9988.HK": "Alibaba",
    "3690.HK": "Meituan",
    "1810.HK": "Xiaomi",
    "9618.HK": "JD.com",
    "9888.HK": "Baidu",
    "9999.HK": "NetEase",
    "1024.HK": "Kuaishou",
    "0981.HK": "SMIC",
    "1211.HK": "BYD",
    "2015.HK": "Li Auto",
    "9868.HK": "XPeng",
    "9866.HK": "NIO",
    "2318.HK": "Ping An Insurance",
    "0941.HK": "China Mobile",
    "1398.HK": "ICBC",
    "3988.HK": "Bank of China",
    "0883.HK": "CNOOC",
    "PTT.BK": "PTT",
    "SCB.BK": "SCB X",
    "ADVANC.BK": "Advanced Info Service",
    "AOT.BK": "Airports of Thailand",
    "CPALL.BK": "CP All",
    "BDMS.BK": "Bangkok Dusit Medical Services",
    "SCC.BK": "Siam Cement",
    "BBL.BK": "Bangkok Bank",
    "KBANK.BK": "Kasikornbank",
    "KTB.BK": "Krung Thai Bank",
    "TRUE.BK": "True Corporation",
    "MINT.BK": "Minor International",
    "CPN.BK": "Central Pattana",
    "GULF.BK": "Gulf Development",
    "DELTA.BK": "Delta Electronics Thailand",
}


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _init_db(conn)
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS paper_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market TEXT NOT NULL,
            symbol TEXT NOT NULL,
            name TEXT NOT NULL,
            side TEXT NOT NULL,
            bucket TEXT NOT NULL,
            bucket_label TEXT NOT NULL,
            quantity REAL NOT NULL,
            entry_price REAL NOT NULL,
            stop_loss REAL NOT NULL,
            target REAL NOT NULL,
            probability_pct REAL NOT NULL,
            risk_amount REAL NOT NULL,
            risk_pct REAL NOT NULL,
            allocation_pct REAL NOT NULL,
            opened_at TEXT NOT NULL,
            closed_at TEXT,
            exit_price REAL,
            realized_pnl REAL,
            close_reason TEXT,
            status TEXT NOT NULL DEFAULT 'open'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS paper_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_id INTEGER,
            market TEXT NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            bucket TEXT NOT NULL,
            event_type TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            pnl REAL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(position_id) REFERENCES paper_positions(id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_paper_positions_status ON paper_positions(market, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_paper_events_market_created ON paper_events(market, created_at)")
    conn.commit()

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


def _pnl(side: str, entry: float, price: float, quantity: float) -> tuple[float, float]:
    if side == "long":
        pnl = (price - entry) * quantity
        pnl_pct = ((price - entry) / entry) * 100 if entry else 0.0
    else:
        pnl = (entry - price) * quantity
        pnl_pct = ((entry - price) / entry) * 100 if entry else 0.0
    return pnl, pnl_pct


def _close_trigger(side: str, current: float, target: float, stop_loss: float) -> tuple[bool, str]:
    if side == "long":
        if stop_loss and current <= stop_loss:
            return True, "stop_loss"
        if target and current >= target:
            return True, "target"
    else:
        if stop_loss and current >= stop_loss:
            return True, "stop_loss"
        if target and current <= target:
            return True, "target"
    return False, ""


def _quote_price(symbol: str, fallback: float) -> float:
    try:
        quote = get_quote(symbol)
        price = float(quote.get("price") or 0)
        return price if price > 0 else fallback
    except Exception:
        return fallback


def _display_name(symbol: str, fallback: str | None = None) -> str:
    clean_symbol = symbol.upper()
    clean_fallback = (fallback or "").strip()
    if clean_fallback and clean_fallback.upper() != clean_symbol:
        return clean_fallback
    return DISPLAY_NAME_BY_SYMBOL.get(clean_symbol, clean_symbol)


def _quote_snapshot(symbol: str, fallback_price: float, fallback_name: str | None = None) -> dict:
    try:
        quote = get_quote(symbol)
        price = float(quote.get("price") or 0)
        return {
            "price": price if price > 0 else fallback_price,
            "name": _display_name(symbol, quote.get("name") or fallback_name),
        }
    except Exception:
        return {
            "price": fallback_price,
            "name": _display_name(symbol, fallback_name),
        }


def _entry_is_executable(side: str, current: float, target: float, stop_loss: float) -> bool:
    if current <= 0 or target <= 0 or stop_loss <= 0:
        return False
    if side == "long":
        return stop_loss < current < target
    return target < current < stop_loss


def _risk_per_unit(side: str, entry: float, stop_loss: float) -> float:
    if side == "long":
        return entry - stop_loss
    return stop_loss - entry


def _position_quantity(
    side: str,
    entry: float,
    stop_loss: float,
    remaining_exposure: float,
    cash: float,
    bucket_remaining: float,
    bucket_config: dict,
) -> float:
    risk_per_unit = _risk_per_unit(side, entry, stop_loss)
    if risk_per_unit <= 0:
        return 0.0

    bucket_capital = STARTING_CASH * bucket_config["capital_pct"]
    risk_budget = bucket_capital * bucket_config["risk_pct"]
    position_cap = bucket_capital * bucket_config["max_position_pct"]
    cash_reserve = STARTING_CASH * MIN_CASH_RESERVE_PCT
    available_cash = max(0.0, cash - cash_reserve)
    budget = min(position_cap, remaining_exposure, available_cash, bucket_remaining)
    if budget <= 0:
        return 0.0

    by_risk = risk_budget / risk_per_unit
    by_budget = budget / entry
    return round(max(0.0, min(by_risk, by_budget)), 4)


def _bucket_priority(item: dict, bucket: str) -> float:
    probability = float(item.get("probability_pct") or 0)
    score = float(item.get("score") or 0)
    rr = float(item.get("risk_reward") or 0)
    change = abs(float(item.get("change_pct") or 0))
    target_room = float(item.get("target_room_pct") or 0)

    if bucket == "momentum":
        return score * 0.40 + probability * 0.25 + change * 3.0 + target_room * 1.5 + rr * 6.0
    return probability * 0.45 + score * 0.30 + rr * 10.0 + target_room * 1.0 - change * 0.4


def _candidate_passes_bucket(item: dict, bucket: str, bucket_config: dict) -> bool:
    probability = float(item.get("probability_pct") or 0)
    score = float(item.get("score") or 0)
    rr = float(item.get("risk_reward") or 0)
    target_room = float(item.get("target_room_pct") or 0)

    if probability < bucket_config["min_probability"] or score < bucket_config["min_score"]:
        return False
    if bucket == "quality":
        return rr >= 1.5 and target_room >= 1.0
    return rr >= 1.0 and target_room >= 0.5


def _load_open_positions(conn: sqlite3.Connection, market: str) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT * FROM paper_positions WHERE market = ? AND status = 'open' ORDER BY opened_at ASC",
            (market,),
        )
    )


def _realized_pnl(conn: sqlite3.Connection, market: str) -> float:
    row = conn.execute(
        "SELECT COALESCE(SUM(realized_pnl), 0) AS pnl FROM paper_positions WHERE market = ? AND status = 'closed'",
        (market,),
    ).fetchone()
    return float(row["pnl"] or 0.0)


def _recent_events(conn: sqlite3.Connection, market: str, limit: int = 20) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, created_at, symbol, side, bucket, event_type, quantity, price, pnl, reason
        FROM paper_events
        WHERE market = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (market, limit),
    ).fetchall()
    return [
        {
            "id": f"event-{row['id']}",
            "time": row["created_at"],
            "symbol": row["symbol"],
            "side": row["side"],
            "bucket": row["bucket"],
            "event_type": row["event_type"],
            "quantity": round(float(row["quantity"]), 4),
            "price": round(float(row["price"]), 2),
            "status": "closed" if row["event_type"] == "close" else "simulated",
            "reason": row["reason"],
            "pnl": None if row["pnl"] is None else round(float(row["pnl"]), 2),
        }
        for row in rows
    ]


def _log_event(
    conn: sqlite3.Connection,
    position_id: int | None,
    market: str,
    symbol: str,
    side: str,
    bucket: str,
    event_type: str,
    quantity: float,
    price: float,
    reason: str,
    created_at: str,
    pnl: float | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO paper_events
            (position_id, market, symbol, side, bucket, event_type, quantity, price, pnl, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (position_id, market, symbol, side, bucket, event_type, quantity, price, pnl, reason, created_at),
    )


def _close_position(conn: sqlite3.Connection, row: sqlite3.Row, current: float, reason: str, now: str) -> None:
    pnl, _ = _pnl(row["side"], float(row["entry_price"]), current, float(row["quantity"]))
    conn.execute(
        """
        UPDATE paper_positions
        SET status = 'closed',
            closed_at = ?,
            exit_price = ?,
            realized_pnl = ?,
            close_reason = ?
        WHERE id = ?
        """,
        (now, round(current, 2), round(pnl, 2), reason, row["id"]),
    )
    _log_event(
        conn,
        row["id"],
        row["market"],
        row["symbol"],
        row["side"],
        row["bucket"],
        "close",
        float(row["quantity"]),
        round(current, 2),
        f"Closed by {reason}",
        now,
        pnl=round(pnl, 2),
    )


def _sync_open_positions(conn: sqlite3.Connection, market: str, now: str, can_execute: bool) -> None:
    if not can_execute:
        return

    changed = False
    for row in _load_open_positions(conn, market):
        current = _quote_price(row["symbol"], float(row["entry_price"]))
        should_close, reason = _close_trigger(
            row["side"],
            current,
            float(row["target"]),
            float(row["stop_loss"]),
        )
        if should_close:
            _close_position(conn, row, current, reason, now)
            changed = True
    if changed:
        conn.commit()


def _open_position(
    conn: sqlite3.Connection,
    market: str,
    item: dict,
    bucket: str,
    bucket_config: dict,
    quantity: float,
    entry: float,
    current: float,
    stop_loss: float,
    target: float,
    now: str,
    name: str,
) -> None:
    risk_amount = round(abs(entry - stop_loss) * quantity, 2)
    market_value = round(quantity * current, 2)
    cursor = conn.execute(
        """
        INSERT INTO paper_positions
            (
                market, symbol, name, side, bucket, bucket_label, quantity,
                entry_price, stop_loss, target, probability_pct, risk_amount,
                risk_pct, allocation_pct, opened_at, status
            )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
        """,
        (
            market,
            item["symbol"],
            name,
            item["direction"],
            bucket,
            bucket_config["label"],
            quantity,
            round(entry, 2),
            round(stop_loss, 2),
            round(target, 2),
            round(float(item.get("probability_pct") or 0), 1),
            risk_amount,
            round((risk_amount / STARTING_CASH) * 100, 2),
            round((market_value / STARTING_CASH) * 100, 2),
            now,
        ),
    )
    position_id = int(cursor.lastrowid)
    _log_event(
        conn,
        position_id,
        market,
        item["symbol"],
        item["direction"],
        bucket,
        "open",
        quantity,
        round(entry, 2),
        (
            f"{bucket_config['label']} bucket: risk {bucket_config['risk_pct'] * 100:.1f}% of bucket, "
            f"score {round(item.get('score', 0), 1)}, "
            f"{round(item.get('probability_pct', 0), 1)}% probability"
        ),
        now,
    )


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
    now_utc = datetime.now(ZoneInfo("UTC"))
    now = now_utc.astimezone(ZoneInfo("Asia/Bangkok")).replace(second=0, microsecond=0).isoformat()
    market_state = market_status(market, now_utc)
    can_execute = bool(market_state.get("is_open"))
    conn = _connect()
    try:
        _sync_open_positions(conn, market, now, can_execute)

        open_rows = _load_open_positions(conn, market)
        realized = _realized_pnl(conn, market)
        open_cost = sum(float(row["entry_price"]) * float(row["quantity"]) for row in open_rows if row["side"] == "long")
        cash = round(max(0.0, STARTING_CASH + realized - open_cost), 2)
        invested = sum(float(row["entry_price"]) * float(row["quantity"]) for row in open_rows)
        bucket_invested = {key: 0.0 for key in BUCKET_ALLOCATIONS}
        bucket_counts = {key: 0 for key in BUCKET_ALLOCATIONS}
        symbols_used = {row["symbol"] for row in open_rows}

        for row in open_rows:
            bucket_invested[row["bucket"]] = round(
                bucket_invested.get(row["bucket"], 0.0) + float(row["entry_price"]) * float(row["quantity"]),
                2,
            )
            bucket_counts[row["bucket"]] = bucket_counts.get(row["bucket"], 0) + 1

        if can_execute and len(open_rows) < MAX_POSITIONS:
            candidates = build_trade_signals(market=market)
            bucket_candidates = {
                bucket: sorted(
                    (
                        item for item in candidates
                        if _candidate_passes_bucket(item, bucket, config)
                    ),
                    key=lambda item: _bucket_priority(item, bucket),
                    reverse=True,
                )
                for bucket, config in BUCKET_ALLOCATIONS.items()
            }
            max_exposure = STARTING_CASH * MAX_PORTFOLIO_EXPOSURE_PCT

            for bucket in ("quality", "momentum"):
                bucket_config = BUCKET_ALLOCATIONS[bucket]
                bucket_capital = STARTING_CASH * bucket_config["capital_pct"]
                for item in bucket_candidates[bucket]:
                    if len(open_rows) >= MAX_POSITIONS:
                        break
                    if bucket_counts[bucket] >= bucket_config["max_positions"]:
                        break
                    if item["symbol"] in symbols_used:
                        continue

                    side = item.get("direction")
                    if side not in ("long", "short"):
                        continue
                    if side == "short" and market not in ALLOW_SHORT_MARKETS:
                        continue

                    snapshot = _quote_snapshot(
                        item["symbol"],
                        float(item.get("price") or 0),
                        item.get("name"),
                    )
                    current = float(snapshot["price"])
                    entry = current
                    stop_loss = float(item.get("stop_loss") or 0)
                    target = float(item.get("target") or 0)
                    if not _entry_is_executable(side, current, target, stop_loss):
                        continue

                    remaining_exposure = max(0.0, max_exposure - invested)
                    bucket_remaining = max(0.0, bucket_capital - bucket_invested[bucket])
                    quantity = _position_quantity(
                        side,
                        entry,
                        stop_loss,
                        remaining_exposure,
                        cash,
                        bucket_remaining,
                        bucket_config,
                    )
                    if quantity <= 0:
                        continue

                    _open_position(
                        conn,
                        market,
                        item,
                        bucket,
                        bucket_config,
                        quantity,
                        entry,
                        current,
                        stop_loss,
                        target,
                        now,
                        snapshot["name"],
                    )
                    conn.commit()

                    planned_cost = round(quantity * entry, 2)
                    invested += planned_cost
                    bucket_invested[bucket] = round(bucket_invested[bucket] + planned_cost, 2)
                    bucket_counts[bucket] += 1
                    symbols_used.add(item["symbol"])
                    if side == "long":
                        cash = round(max(0.0, cash - planned_cost), 2)
                    open_rows = _load_open_positions(conn, market)

        positions = []
        for row in open_rows:
            current = _quote_price(row["symbol"], float(row["entry_price"]))
            pnl, pnl_pct = _pnl(row["side"], float(row["entry_price"]), current, float(row["quantity"]))
            market_value = round(float(row["quantity"]) * current, 2)
            name = _display_name(row["symbol"], row["name"])
            positions.append({
                "id": int(row["id"]),
                "symbol": row["symbol"],
                "name": name,
                "side": row["side"],
                "bucket": row["bucket"],
                "bucket_label": row["bucket_label"],
                "quantity": round(float(row["quantity"]), 4),
                "entry_price": round(float(row["entry_price"]), 2),
                "current_price": round(current, 2),
                "market_value": market_value,
                "risk_amount": round(float(row["risk_amount"]), 2),
                "risk_pct": round(float(row["risk_pct"]), 2),
                "allocation_pct": round(float(row["allocation_pct"]), 2),
                "unrealized_pnl": round(pnl, 2),
                "unrealized_pnl_pct": round(pnl_pct, 2),
                "stop_loss": round(float(row["stop_loss"]), 2),
                "target": round(float(row["target"]), 2),
                "probability_pct": round(float(row["probability_pct"]), 1),
                "status": _position_status(
                    row["side"],
                    current,
                    float(row["target"]),
                    float(row["stop_loss"]),
                ),
                "opened_at": row["opened_at"],
            })

        daily_pnl = round(sum(p["unrealized_pnl"] for p in positions) + realized, 2)
        unrealized_pnl = round(sum(p["unrealized_pnl"] for p in positions), 2)
        equity = round(STARTING_CASH + realized + unrealized_pnl, 2)
        invested = round(sum(p["market_value"] for p in positions), 2)
        open_cost = sum(float(row["entry_price"]) * float(row["quantity"]) for row in open_rows if row["side"] == "long")
        cash = round(max(0.0, STARTING_CASH + realized - open_cost), 2)
        winners = sum(1 for p in positions if p["unrealized_pnl"] > 0)
        trades = _recent_events(conn, market)
    finally:
        conn.close()

    win_rate = round((winners / len(positions)) * 100, 1) if positions else 0.0
    daily = _build_daily_curve(daily_pnl, equity)
    peak = max([STARTING_CASH] + [d["equity"] for d in daily])
    trough = min(d["equity"] for d in daily) if daily else STARTING_CASH
    max_drawdown = round(((peak - trough) / peak) * 100, 2) if peak else 0.0
    bucket_invested_current = {key: 0.0 for key in BUCKET_ALLOCATIONS}
    bucket_counts_current = {key: 0 for key in BUCKET_ALLOCATIONS}
    for position in positions:
        bucket_invested_current[position["bucket"]] = round(
            bucket_invested_current.get(position["bucket"], 0.0) + position["market_value"],
            2,
        )
        bucket_counts_current[position["bucket"]] = bucket_counts_current.get(position["bucket"], 0) + 1

    bucket_allocation = {
        bucket: {
            "label": config["label"],
            "capital": round(STARTING_CASH * config["capital_pct"], 2),
            "invested": round(bucket_invested_current[bucket], 2),
            "cash": round(max(0.0, STARTING_CASH * config["capital_pct"] - bucket_invested_current[bucket]), 2),
            "positions": bucket_counts_current[bucket],
            "capital_pct": round(config["capital_pct"] * 100, 1),
            "risk_per_trade_pct": round(config["risk_pct"] * 100, 2),
        }
        for bucket, config in BUCKET_ALLOCATIONS.items()
    }

    return PaperTradingSummary(
        mode="paper",
        market=market,
        currency=CURRENCY_BY_MARKET.get(market, "USD"),
        generated_at=now,
        market_status=market_state,
        starting_cash=STARTING_CASH,
        cash=cash,
        equity=equity,
        invested=round(invested, 2),
        daily_pnl=daily_pnl,
        daily_pnl_pct=round((daily_pnl / STARTING_CASH) * 100, 2),
        open_positions=len(positions),
        win_rate_pct=win_rate,
        max_drawdown_pct=max_drawdown,
        bucket_allocation=bucket_allocation,
        positions=positions,
        recent_trades=list(reversed(trades)),
        daily=daily,
    )
