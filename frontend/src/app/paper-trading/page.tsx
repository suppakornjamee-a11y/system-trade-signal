"use client";

import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { useLang } from "@/lib/context/LanguageContext";
import type { Market, PaperDailyPnL, PaperPosition, PaperTrade, PaperTradingSummary } from "@/lib/types";

const MARKETS: Market[] = ["us", "th", "cn", "gold", "crypto"];
const MARKET_LABELS: Record<"en" | "th", Record<Market, string>> = {
  en: { us: "US", th: "Thailand", cn: "China", gold: "Gold", crypto: "Crypto" },
  th: { us: "สหรัฐ", th: "ไทย", cn: "จีน", gold: "ทองคำ", crypto: "คริปโต" },
};

const COPY = {
  en: {
    phase: "Phase 1",
    paperMode: "Paper mode only",
    title: "Paper Trading Dashboard",
    subtitle:
      "Daily simulated performance, open risk, and auto-generated paper orders from the current market radar.",
    accountEquity: "Account Equity",
    startedWith: "Started with",
    todayPnl: "Today P/L",
    ofStartingCash: "of starting cash",
    openPositions: "Open Positions",
    paperBasket: "paper basket",
    winRate: "Win Rate",
    maxDrawdown: "Max drawdown",
    allocation: "Allocation",
    allocationSub: "Simulated capital usage",
    invested: "Invested",
    cash: "Cash",
    investedPct: "invested",
    available: "still available for new paper trades",
    dailyPnl: "Daily P/L",
    dailySub: "Green days above the line, red days below it",
    lastSessions: "Last {count} sessions",
    positionsSub: "Scan P/L, risk distance, and trade status at a glance",
    noPositions: "No paper positions passed the current signal and risk filters.",
    marketValue: "Market Value",
    units: "units",
    stop: "Stop",
    target: "Target",
    entry: "Entry",
    recentOrders: "Recent Paper Orders",
    recentOrdersSub: "Entry and exit logs stored in the paper ledger",
    noOrders: "No simulated orders today.",
    error: "Failed to load paper trading data. Make sure the backend is running.",
    disclaimer: "No live orders are sent. This is a simulation layer for strategy review and UI validation.",
    plannedRisk: "Planned Risk",
    allocationPct: "Allocation",
    realMoneyMode: "Real-money style sizing: max 1% risk per trade, max 20% allocation per position, and cash reserve stays protected.",
    bucketsTitle: "50/50 Portfolio Split",
    momentumBucket: "Momentum",
    qualityBucket: "Quality",
    momentumDesc: "Faster setups with controlled risk",
    qualityDesc: "Higher-confidence setups with tighter sizing",
    bucketCapital: "Capital",
    bucketRisk: "Risk/trade",
    bucketCash: "Cash left",
    marketOpen: "Market open",
    marketClosed: "Market closed",
    marketClock: "Exchange time",
    marketClosedNote: "No new entries or exits are simulated while this market is closed. Existing positions are only marked with the latest available quote.",
  },
  th: {
    phase: "เฟส 1",
    paperMode: "โหมดจำลองเท่านั้น",
    title: "แดชบอร์ด Paper Trading",
    subtitle: "ดูผลงานจำลองรายวัน ความเสี่ยงของสถานะ และคำสั่งจำลองจากสัญญาณตลาดล่าสุด",
    accountEquity: "มูลค่าพอร์ต",
    startedWith: "เริ่มต้นด้วย",
    todayPnl: "กำไร/ขาดทุนวันนี้",
    ofStartingCash: "ของเงินเริ่มต้น",
    openPositions: "สถานะเปิด",
    paperBasket: "ชุดจำลอง",
    winRate: "อัตราชนะ",
    maxDrawdown: "ขาดทุนสะสมสูงสุด",
    allocation: "การจัดสรรเงิน",
    allocationSub: "การใช้เงินในพอร์ตจำลอง",
    invested: "ลงทุนแล้ว",
    cash: "เงินสด",
    investedPct: "ลงทุนแล้ว",
    available: "ยังเหลือสำหรับเปิดสถานะจำลองใหม่",
    dailyPnl: "กำไร/ขาดทุนรายวัน",
    dailySub: "วันบวกอยู่เหนือเส้น วันลบอยู่ใต้เส้น",
    lastSessions: "{count} วันล่าสุด",
    positionsSub: "ดู P/L ระยะห่างความเสี่ยง และสถานะของไม้ได้ในหน้าเดียว",
    noPositions: "ยังไม่มีสถานะจำลองที่ผ่านเงื่อนไขสัญญาณและความเสี่ยง",
    marketValue: "มูลค่าสถานะ",
    units: "หน่วย",
    stop: "จุดตัดขาดทุน",
    target: "เป้าหมาย",
    entry: "จุดเข้า",
    recentOrders: "คำสั่งจำลองล่าสุด",
    recentOrdersSub: "บันทึกการเข้าออกที่เก็บใน paper ledger",
    noOrders: "วันนี้ยังไม่มีคำสั่งจำลอง",
    error: "โหลดข้อมูล Paper Trading ไม่สำเร็จ ตรวจสอบว่า backend รันอยู่",
    disclaimer: "หน้านี้ไม่ส่งคำสั่งเงินจริง เป็นชั้นจำลองสำหรับทดสอบกลยุทธ์และตรวจ UI เท่านั้น",
    plannedRisk: "ความเสี่ยงที่วางไว้",
    allocationPct: "สัดส่วนพอร์ต",
    realMoneyMode: "คำนวณขนาดไม้แบบเงินจริง: เสี่ยงไม่เกิน 1% ต่อไม้ ลงไม่เกิน 20% ต่อสถานะ และกันเงินสดสำรองไว้เสมอ",
    bucketsTitle: "แบ่งพอร์ต 50/50",
    momentumBucket: "สายซิ่ง",
    qualityBucket: "สายเน้นชัว",
    momentumDesc: "ไม้ไว เน้นโมเมนตัม แต่คุมความเสี่ยง",
    qualityDesc: "ไม้ที่เงื่อนไขแน่นกว่าและลดขนาดความเสี่ยง",
    bucketCapital: "งบ",
    bucketRisk: "เสี่ยง/ไม้",
    bucketCash: "เงินเหลือ",
    marketOpen: "ตลาดเปิด",
    marketClosed: "ตลาดปิด",
    marketClock: "เวลาตลาด",
    marketClosedNote: "ตลาดนี้ยังไม่เปิด ระบบจะไม่จำลองการเข้า/ออกไม้ใหม่ และจะแสดงราคาล่าสุดเท่าที่แหล่งข้อมูลมีเท่านั้น",
  },
};

function money(value: number, currency: string) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}

function compactMoney(value: number, currency: string) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(value);
}

function number(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--:--";
  return date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

function formatMarketTime(value?: string) {
  if (!value) return "--:--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--:--";
  return date.toLocaleString("en-US", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function pnlClass(value: number) {
  if (value > 0) return "text-bull";
  if (value < 0) return "text-bear";
  return "text-neutral";
}

function pnlBg(value: number) {
  if (value > 0) return "bg-bull";
  if (value < 0) return "bg-bear";
  return "bg-neutral";
}

function statusStyle(status: PaperPosition["status"]) {
  if (status === "target_near") return "border-bull/40 bg-bull/10 text-bull";
  if (status === "stop_near") return "border-bear/40 bg-bear/10 text-bear";
  return "border-accent/30 bg-accent/10 text-accent";
}

function bucketLabel(bucket: PaperPosition["bucket"] | PaperTrade["bucket"], copy: typeof COPY.en) {
  return bucket === "momentum" ? copy.momentumBucket : copy.qualityBucket;
}

function bucketStyle(bucket: PaperPosition["bucket"] | PaperTrade["bucket"]) {
  return bucket === "momentum"
    ? "border-yellow-400/40 bg-yellow-400/10 text-yellow-300"
    : "border-accent/40 bg-accent/10 text-accent";
}

function StatCard({
  label,
  value,
  detail,
  tone,
  accent,
}: {
  label: string;
  value: string;
  detail?: string;
  tone?: string;
  accent?: "blue" | "green" | "red" | "amber";
}) {
  const accentClass = {
    blue: "from-accent/25",
    green: "from-bull/25",
    red: "from-bear/25",
    amber: "from-yellow-400/25",
  }[accent || "blue"];

  return (
    <div className={`rounded-lg border border-border bg-gradient-to-br ${accentClass} to-surface p-4`}>
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral">{label}</p>
      <p className={`mt-2 text-2xl font-bold leading-tight ${tone || "text-white"}`}>{value}</p>
      {detail && <p className="mt-2 text-xs text-neutral">{detail}</p>}
    </div>
  );
}

function MarketTabs({
  market,
  onChange,
  lang,
}: {
  market: Market;
  onChange: (market: Market) => void;
  lang: "en" | "th";
}) {
  return (
    <div className="flex w-full gap-1 overflow-x-auto rounded-lg border border-border bg-bg p-1 sm:w-auto">
      {MARKETS.map((id) => (
        <button
          key={id}
          onClick={() => onChange(id)}
          className={`min-w-20 rounded-md px-3 py-2 text-sm font-semibold transition ${
            market === id ? "bg-accent text-bg shadow" : "text-neutral hover:bg-surface hover:text-white"
          }`}
          title={MARKET_LABELS[lang][id]}
        >
          {MARKET_LABELS[lang][id]}
        </button>
      ))}
    </div>
  );
}

function MarketStatusBanner({
  summary,
  copy,
}: {
  summary: PaperTradingSummary;
  copy: typeof COPY.en;
}) {
  const isOpen = summary.market_status?.is_open;

  return (
    <div
      className={`rounded-lg border px-4 py-3 ${
        isOpen
          ? "border-bull/30 bg-bull/10 text-bull"
          : "border-yellow-400/30 bg-yellow-400/10 text-yellow-200"
      }`}
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-bold">
            {isOpen ? copy.marketOpen : copy.marketClosed}
          </p>
          {!isOpen && <p className="mt-1 text-xs text-yellow-100/80">{copy.marketClosedNote}</p>}
        </div>
        <div className="text-xs font-semibold text-current/80">
          {copy.marketClock}: {formatMarketTime(summary.market_status?.local_time)}
          {summary.market_status?.timezone ? ` (${summary.market_status.timezone})` : ""}
        </div>
      </div>
    </div>
  );
}

function AllocationMeter({
  cash,
  invested,
  currency,
  copy,
}: {
  cash: number;
  invested: number;
  currency: string;
  copy: typeof COPY.en;
}) {
  const total = Math.max(1, cash + invested);
  const investedPct = Math.round((invested / total) * 100);
  const cashPct = 100 - investedPct;

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-bold text-white">{copy.allocation}</h2>
          <p className="text-xs text-neutral">{copy.allocationSub}</p>
        </div>
        <span className="rounded border border-border bg-bg px-2 py-1 text-xs font-semibold text-neutral">
          {investedPct}% {copy.investedPct}
        </span>
      </div>
      <div className="mt-4 h-3 overflow-hidden rounded-full bg-bg">
        <div className="h-full bg-accent" style={{ width: `${investedPct}%` }} />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-xs text-neutral">{copy.invested}</p>
          <p className="font-mono font-bold text-white">{compactMoney(invested, currency)}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-neutral">{copy.cash}</p>
          <p className="font-mono font-bold text-white">{compactMoney(cash, currency)}</p>
        </div>
      </div>
      <p className="mt-2 text-[11px] text-neutral">{cashPct}% {copy.available}</p>
    </div>
  );
}

function BucketSplit({
  summary,
  currency,
  copy,
}: {
  summary: PaperTradingSummary;
  currency: string;
  copy: typeof COPY.en;
}) {
  const buckets: Array<"momentum" | "quality"> = ["momentum", "quality"];

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="mb-4">
        <h2 className="text-lg font-bold">{copy.bucketsTitle}</h2>
        <p className="text-xs text-neutral">{copy.realMoneyMode}</p>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {buckets.map((bucket) => {
          const data = summary.bucket_allocation[bucket];
          const usedPct = data.capital ? Math.round((data.invested / data.capital) * 100) : 0;
          return (
            <div key={bucket} className="rounded-lg border border-border bg-bg p-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <span className={`rounded border px-2 py-1 text-xs font-bold ${bucketStyle(bucket)}`}>
                    {bucketLabel(bucket, copy)}
                  </span>
                  <p className="mt-2 text-xs text-neutral">
                    {bucket === "momentum" ? copy.momentumDesc : copy.qualityDesc}
                  </p>
                </div>
                <span className="font-mono text-sm font-bold text-white">{data.capital_pct.toFixed(0)}%</span>
              </div>
              <div className="mt-3 h-2 rounded-full bg-surface">
                <div
                  className={bucket === "momentum" ? "h-full rounded-full bg-yellow-400" : "h-full rounded-full bg-accent"}
                  style={{ width: `${Math.min(100, usedPct)}%` }}
                />
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                <div>
                  <p className="text-neutral">{copy.bucketCapital}</p>
                  <p className="font-mono font-bold text-white">{compactMoney(data.capital, currency)}</p>
                </div>
                <div>
                  <p className="text-neutral">{copy.invested}</p>
                  <p className="font-mono font-bold text-white">{compactMoney(data.invested, currency)}</p>
                </div>
                <div>
                  <p className="text-neutral">{copy.bucketRisk}</p>
                  <p className="font-mono font-bold text-white">{data.risk_per_trade_pct.toFixed(2)}%</p>
                </div>
              </div>
              <p className="mt-2 text-[11px] text-neutral">
                {data.positions} {copy.openPositions.toLowerCase()} · {copy.bucketCash} {compactMoney(data.cash, currency)}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DailyBars({
  daily,
  currency,
  copy,
}: {
  daily: PaperDailyPnL[];
  currency: string;
  copy: typeof COPY.en;
}) {
  const maxAbs = Math.max(1, ...daily.map((d) => Math.abs(d.pnl)));

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">{copy.dailyPnl}</h2>
          <p className="text-xs text-neutral">{copy.dailySub}</p>
        </div>
        <div className="rounded border border-border bg-bg px-3 py-1 text-xs text-neutral">
          {copy.lastSessions.replace("{count}", String(daily.length))}
        </div>
      </div>

      <div className="relative h-64 rounded-md border border-border bg-bg/60 px-3 py-5">
        <div className="absolute left-3 right-3 top-1/2 h-px bg-border" />
        <div className="grid h-full grid-cols-10 items-center gap-2">
          {daily.map((day) => {
            const positive = day.pnl >= 0;
            const height = Math.max(8, Math.round((Math.abs(day.pnl) / maxAbs) * 104));
            return (
              <div key={day.date} className="flex h-full flex-col items-center justify-center">
                <div className="flex h-1/2 w-full items-end">
                  {positive && (
                    <div
                      title={`${day.date}: ${money(day.pnl, currency)}`}
                      className={`w-full rounded-t ${pnlBg(day.pnl)}`}
                      style={{ height }}
                    />
                  )}
                </div>
                <div className="flex h-1/2 w-full items-start">
                  {!positive && (
                    <div
                      title={`${day.date}: ${money(day.pnl, currency)}`}
                      className={`w-full rounded-b ${pnlBg(day.pnl)}`}
                      style={{ height }}
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-3 grid grid-cols-10 gap-2 text-center text-[10px] text-neutral">
        {daily.map((day) => (
          <span key={day.date}>{day.date.slice(5)}</span>
        ))}
      </div>
    </div>
  );
}

function PositionCard({
  position,
  currency,
  copy,
}: {
  position: PaperPosition;
  currency: string;
  copy: typeof COPY.en;
}) {
  const positive = position.unrealized_pnl >= 0;
  const range = Math.max(0.01, Math.abs(position.target - position.stop_loss));
  const progress = Math.max(
    0,
    Math.min(100, ((position.current_price - position.stop_loss) / range) * 100)
  );

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-lg font-bold text-white">{position.name}</h3>
            <span
              className={`rounded border px-2 py-0.5 text-[11px] font-bold uppercase ${
                position.side === "long"
                  ? "border-bull/40 bg-bull/10 text-bull"
                  : "border-bear/40 bg-bear/10 text-bear"
              }`}
            >
              {position.side}
            </span>
            <span className={`rounded border px-2 py-0.5 text-[11px] font-bold ${bucketStyle(position.bucket)}`}>
              {bucketLabel(position.bucket, copy)}
            </span>
          </div>
          <p className="truncate text-xs text-neutral">{position.symbol}</p>
        </div>
        <span className={`rounded border px-2 py-1 text-[11px] font-semibold ${statusStyle(position.status)}`}>
          {position.status.replace("_", " ")}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <div>
          <p className="text-xs text-neutral">P/L</p>
          <p className={`font-mono text-xl font-bold ${pnlClass(position.unrealized_pnl)}`}>
            {money(position.unrealized_pnl, currency)}
          </p>
          <p className={`text-xs ${pnlClass(position.unrealized_pnl)}`}>
            {positive ? "+" : ""}
            {position.unrealized_pnl_pct.toFixed(2)}%
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-neutral">{copy.marketValue}</p>
          <p className="font-mono text-xl font-bold text-white">
            {compactMoney(position.market_value, currency)}
          </p>
          <p className="text-xs text-neutral">{number(position.quantity)} {copy.units}</p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 rounded-md border border-border bg-bg px-3 py-2 text-sm">
        <div>
          <p className="text-[11px] text-neutral">{copy.plannedRisk}</p>
          <p className="font-mono font-bold text-bear">
            {money(position.risk_amount, currency)}
            <span className="ml-1 text-xs">({position.risk_pct.toFixed(2)}%)</span>
          </p>
        </div>
        <div className="text-right">
          <p className="text-[11px] text-neutral">{copy.allocationPct}</p>
          <p className="font-mono font-bold text-white">{position.allocation_pct.toFixed(2)}%</p>
        </div>
      </div>

      <div className="mt-4">
        <div className="mb-2 flex justify-between text-[11px] text-neutral">
          <span>{copy.stop} {money(position.stop_loss, currency)}</span>
          <span>{copy.target} {money(position.target, currency)}</span>
        </div>
        <div className="h-2 rounded-full bg-bg">
          <div className="h-full rounded-full bg-accent" style={{ width: `${progress}%` }} />
        </div>
        <div className="mt-2 flex justify-between text-xs">
          <span className="text-neutral">{copy.entry} {money(position.entry_price, currency)}</span>
          <span className="font-mono text-white">{money(position.current_price, currency)}</span>
        </div>
      </div>
    </div>
  );
}

function Positions({
  positions,
  currency,
  copy,
}: {
  positions: PaperPosition[];
  currency: string;
  copy: typeof COPY.en;
}) {
  return (
    <div className="rounded-lg border border-border bg-bg p-1">
      <div className="flex flex-wrap items-center justify-between gap-3 px-3 py-3">
        <div>
          <h2 className="text-lg font-bold">{copy.openPositions}</h2>
          <p className="text-xs text-neutral">{copy.positionsSub}</p>
        </div>
      </div>

      {positions.length ? (
        <div className="grid grid-cols-1 gap-3 p-3 lg:grid-cols-2">
          {positions.map((position) => (
            <PositionCard key={position.symbol} position={position} currency={currency} copy={copy} />
          ))}
        </div>
      ) : (
        <div className="rounded-lg bg-surface px-4 py-12 text-center text-neutral">
          {copy.noPositions}
        </div>
      )}
    </div>
  );
}

function TradesList({
  trades,
  currency,
  copy,
}: {
  trades: PaperTrade[];
  currency: string;
  copy: typeof COPY.en;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">{copy.recentOrders}</h2>
          <p className="text-xs text-neutral">{copy.recentOrdersSub}</p>
        </div>
      </div>
      <div className="space-y-2">
        {trades.map((trade) => (
          <div
            key={trade.id}
            className="grid grid-cols-[auto_1fr_auto] items-center gap-3 rounded-md border border-border bg-bg px-3 py-3 text-sm"
          >
            <div
              className={`h-9 w-1 rounded-full ${
                trade.side === "long" ? "bg-bull" : "bg-bear"
              }`}
            />
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <span className="font-bold text-white">{trade.symbol}</span>
                <span className="text-xs font-semibold uppercase text-neutral">{trade.side}</span>
                <span
                  className={`rounded border px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                    trade.event_type === "close"
                      ? "border-bear/40 bg-bear/10 text-bear"
                      : "border-bull/40 bg-bull/10 text-bull"
                  }`}
                >
                  {trade.event_type}
                </span>
                <span className={`rounded border px-1.5 py-0.5 text-[10px] font-bold ${bucketStyle(trade.bucket)}`}>
                  {bucketLabel(trade.bucket, copy)}
                </span>
                <span className="font-mono text-xs text-neutral">
                  {number(trade.quantity)} @ {money(trade.price, currency)}
                </span>
                {trade.pnl !== null && (
                  <span className={`font-mono text-xs font-bold ${pnlClass(trade.pnl)}`}>
                    {money(trade.pnl, currency)}
                  </span>
                )}
              </div>
              <p className="mt-1 truncate text-xs text-neutral">{trade.reason}</p>
            </div>
            <div className="text-right text-xs text-neutral">{formatTime(trade.time)}</div>
          </div>
        ))}
        {!trades.length && <p className="py-6 text-center text-neutral">{copy.noOrders}</p>}
      </div>
    </div>
  );
}

export default function PaperTradingPage() {
  const { lang } = useLang();
  const uiLang = lang === "th" ? "th" : "en";
  const copy = COPY[uiLang];
  const [market, setMarket] = useState<Market>("us");
  const { data, error, isLoading } = useSWR(
    `paper-trading-${market}`,
    () => api.paperTradingSummary(market),
    { refreshInterval: 60_000 }
  );

  return (
    <div className="space-y-5">
      <section className="rounded-lg border border-border bg-surface p-5">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="rounded border border-accent/40 bg-accent/10 px-2 py-1 text-xs font-bold uppercase tracking-wide text-accent">
                {copy.phase}
              </span>
              <span className="rounded border border-border bg-bg px-2 py-1 text-xs font-semibold text-neutral">
                {copy.paperMode}
              </span>
            </div>
            <h1 className="text-3xl font-bold leading-tight text-white">{copy.title}</h1>
            <p className="mt-2 max-w-2xl text-sm text-neutral">
              {copy.subtitle}
            </p>
            <p className="mt-2 max-w-3xl text-xs text-accent">
              {copy.realMoneyMode}
            </p>
          </div>
          <MarketTabs market={market} onChange={setMarket} lang={uiLang} />
        </div>
      </section>

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-lg border border-border bg-surface" />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-bear/40 bg-bear/10 p-6 text-bear">
          {copy.error}
        </div>
      )}

      {data && (
        <>
          <MarketStatusBanner summary={data} copy={copy} />

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
            <div className="xl:col-span-2">
              <StatCard
                label={copy.accountEquity}
                value={money(data.equity, data.currency)}
                detail={`${copy.startedWith} ${money(data.starting_cash, data.currency)}`}
                accent="blue"
              />
            </div>
            <StatCard
              label={copy.todayPnl}
              value={money(data.daily_pnl, data.currency)}
              detail={`${data.daily_pnl_pct.toFixed(2)}% ${copy.ofStartingCash}`}
              tone={pnlClass(data.daily_pnl)}
              accent={data.daily_pnl >= 0 ? "green" : "red"}
            />
            <StatCard
              label={copy.openPositions}
              value={String(data.open_positions)}
              detail={`${MARKET_LABELS[uiLang][data.market]} ${copy.paperBasket}`}
              accent="amber"
            />
            <StatCard
              label={copy.winRate}
              value={`${data.win_rate_pct.toFixed(1)}%`}
              detail={`${copy.maxDrawdown} ${data.max_drawdown_pct.toFixed(2)}%`}
              accent="blue"
            />
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1fr_320px]">
            <DailyBars daily={data.daily} currency={data.currency} copy={copy} />
            <AllocationMeter cash={data.cash} invested={data.invested} currency={data.currency} copy={copy} />
          </div>

          <BucketSplit summary={data} currency={data.currency} copy={copy} />

          <Positions positions={data.positions} currency={data.currency} copy={copy} />

          <TradesList trades={data.recent_trades} currency={data.currency} copy={copy} />

          <p className="text-center text-[11px] text-neutral">
            {copy.disclaimer}
          </p>
        </>
      )}
    </div>
  );
}
