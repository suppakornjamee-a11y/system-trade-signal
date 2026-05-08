"use client";
import Link from "next/link";
import { useState } from "react";
import type { StockSummary } from "@/lib/types";
import { MARKET_CURRENCY } from "@/lib/types";
import type { Market } from "@/lib/types";
import { useLang } from "@/lib/context/LanguageContext";
import RankBadge from "@/components/RankBadge";
import { clsx } from "clsx";
import { getLogoUrl, symbolColor, displaySymbol } from "@/lib/logos";

function LogoAvatar({ symbol, market }: { symbol: string; market: Market }) {
  const url = getLogoUrl(symbol, market);
  const [failed, setFailed] = useState(false);
  const disp = displaySymbol(symbol);

  if (url && !failed) {
    return (
      <img
        src={url}
        alt={symbol}
        width={28}
        height={28}
        className="w-7 h-7 rounded object-contain bg-white/5 shrink-0"
        onError={() => setFailed(true)}
      />
    );
  }

  return (
    <span className={clsx("w-7 h-7 rounded flex items-center justify-center text-xs font-bold text-white shrink-0", symbolColor(symbol))}>
      {disp[0]}
    </span>
  );
}

function fmt(n: number, decimals = 2) {
  return n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function fmtVol(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

function actionCopy(action: string, lang: string) {
  const th = lang === "th";
  if (action === "ready") {
    return {
      label: th ? "เข้าได้ตอนนี้" : "Ready now",
      note: th ? "ราคาอยู่ในโซนเข้าแล้ว" : "Price is inside the entry zone",
      color: "text-bull border-bull/40 bg-bull/10",
    };
  }
  if (action === "wait_bounce") {
    return {
      label: th ? "รอเด้ง" : "Wait bounce",
      note: th ? "ยังไม่ใช่จุดขาย/ชอร์ตที่ดี" : "Not at a clean short zone yet",
      color: "text-yellow-400 border-yellow-400/40 bg-yellow-400/10",
    };
  }
  return {
    label: th ? "รอย่อ" : "Wait pullback",
    note: th ? "อย่าไล่ราคา รอเข้าใกล้โซน" : "Do not chase; wait near the zone",
    color: "text-yellow-400 border-yellow-400/40 bg-yellow-400/10",
  };
}

const SIGNAL_COLOR = {
  bullish: "text-bull border-bull/30",
  bearish: "text-bear border-bear/30",
  neutral: "text-neutral border-neutral/30",
};

const SIGNAL_BG = {
  bullish: "bg-bull/10",
  bearish: "bg-bear/10",
  neutral: "bg-neutral/10",
};

export default function StockCard({ stock }: { stock: StockSummary }) {
  const { t, lang } = useLang();
  const { trade_setup: ts } = stock;
  const positive = stock.change >= 0;
  const cur = MARKET_CURRENCY[stock.market] ?? "$";
  const action = actionCopy(ts.action, lang);

  const signalLabel =
    stock.signal === "bullish"
      ? t("card.signal_long")
      : stock.signal === "bearish"
      ? t("card.signal_short")
      : t("card.signal_watch");

  const newsLabel =
    stock.news_sentiment === "bullish"
      ? t("news.bullish")
      : stock.news_sentiment === "bearish"
      ? t("news.bearish")
      : t("news.neutral");

  return (
    <Link href={`/stock/${stock.symbol}`}>
      <div className={clsx(
        "border rounded-lg p-4 bg-surface hover:bg-surface/80 transition cursor-pointer",
        SIGNAL_COLOR[stock.signal]
      )}>
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 min-w-0">
            <LogoAvatar symbol={stock.symbol} market={stock.market} />
            <div className="min-w-0 flex items-center gap-1.5 flex-wrap">
              <span className="font-bold text-white text-lg leading-none">{displaySymbol(stock.symbol)}</span>
              {stock.name && stock.name.toUpperCase() !== displaySymbol(stock.symbol).toUpperCase() && (
                <span className="text-xs text-neutral truncate max-w-[90px]">{stock.name}</span>
              )}
              <RankBadge rank={stock.momentum_rank} size="sm" />
            </div>
          </div>
          <span className={clsx(
            "text-xs font-bold px-2 py-0.5 rounded border shrink-0",
            SIGNAL_COLOR[stock.signal], SIGNAL_BG[stock.signal]
          )}>
            {signalLabel}
          </span>
        </div>

        <div className={clsx("mb-3 rounded border px-3 py-2", action.color)}>
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-bold">{action.label}</span>
            <span className="text-[11px] font-mono">
              E {ts.entry_distance_pct.toFixed(2)}% | T {ts.target_room_pct.toFixed(2)}%
            </span>
          </div>
          <div className="mt-0.5 text-[11px] opacity-80">{action.note}</div>
        </div>

        {/* Price */}
        <div className="flex items-baseline gap-3 mb-3">
          <span className="text-2xl font-mono font-bold text-white">
            {cur}{fmt(stock.price)}
          </span>
          <span className={clsx("text-sm font-mono", positive ? "text-bull" : "text-bear")}>
            {positive ? "+" : ""}{fmt(stock.change)} ({positive ? "+" : ""}{fmt(stock.change_pct)}%)
          </span>
        </div>

        {/* Trade Setup — ordered low→high so direction is visually obvious */}
        {(() => {
          const isShort = ts.direction === "short";
          // For LONG: SL(low) | Entry(mid) | Target(high)
          // For SHORT: Target(low) | Entry(mid) | SL(high)
          const boxes = isShort
            ? [
                { label: t("card.target"), value: ts.target, color: "text-bull" },
                { label: t("card.entry"), value: ts.entry, color: "text-white" },
                { label: t("card.stop_loss"), value: ts.stop_loss, color: "text-bear" },
              ]
            : [
                { label: t("card.stop_loss"), value: ts.stop_loss, color: "text-bear" },
                { label: t("card.entry"), value: ts.entry, color: "text-white" },
                { label: t("card.target"), value: ts.target, color: "text-bull" },
              ];
          return (
            <div className="grid grid-cols-3 gap-2 text-xs mb-3">
              {boxes.map((b) => (
                <div key={b.label} className="bg-bg rounded p-2">
                  <div className="text-neutral mb-0.5">{b.label}</div>
                  <div className={clsx("font-mono font-semibold", b.color)}>{cur}{fmt(b.value)}</div>
                </div>
              ))}
              {/* Direction arrow under the 3 boxes */}
              <div className="col-span-3 flex items-center justify-center gap-1 text-[10px] text-neutral mt-0.5">
                {isShort ? (
                  <><span className="text-bear">▼ {t("card.stop_loss")} → {t("card.entry")} → {t("card.target")}</span></>
                ) : (
                  <><span className="text-bull">▲ {t("card.stop_loss")} → {t("card.entry")} → {t("card.target")}</span></>
                )}
              </div>
            </div>
          );
        })()}

        {/* Probability bar */}
        <div className="mb-2">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-neutral">{t("card.win_prob")}</span>
            <span className={clsx("font-bold",
              ts.probability_pct >= 55 ? "text-bull" :
              ts.probability_pct >= 45 ? "text-yellow-400" : "text-bear"
            )}>
              {ts.probability_pct}%
            </span>
          </div>
          <div className="h-1.5 bg-bg rounded-full overflow-hidden">
            <div
              className={clsx("h-full rounded-full transition-all",
                ts.probability_pct >= 55 ? "bg-bull" :
                ts.probability_pct >= 45 ? "bg-yellow-400" : "bg-bear"
              )}
              style={{ width: `${ts.probability_pct}%` }}
            />
          </div>
        </div>

        {/* Footer stats */}
        <div className="flex justify-between text-xs text-neutral mt-2">
          <span>{t("card.vol")} {fmtVol(stock.volume)} ({fmt(stock.volume_ratio, 1)}x)</span>
          <span>{t("card.rr")} {fmt(ts.risk_reward, 1)}x</span>
          <span className={clsx(
            stock.news_sentiment === "bullish" ? "text-bull" :
            stock.news_sentiment === "bearish" ? "text-bear" : "text-neutral"
          )}>
            {stock.news_count} {t("card.news")} · {t("card.overall")}: {newsLabel}
          </span>
        </div>
      </div>
    </Link>
  );
}
