"use client";
import { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { api } from "@/lib/api";
import { displaySymbol } from "@/lib/logos";
import { useLang } from "@/lib/context/LanguageContext";
import { useWebSocket } from "@/lib/hooks/useWebSocket";
import TradingChart from "@/components/TradingChart";
import TradeSetupCard from "@/components/TradeSetupCard";
import ProbabilityMeter from "@/components/ProbabilityMeter";
import NewsFeed from "@/components/NewsFeed";
import { clsx } from "clsx";

type Period = "1d" | "5d" | "1mo" | "3mo";
type Interval = "5m" | "15m" | "1h" | "1d";
type Tab = "overview" | "news";

const PERIOD_INTERVAL: Record<Period, Interval> = {
  "1d": "5m",
  "5d": "15m",
  "1mo": "1h",
  "3mo": "1d",
};

function fmt(n: number, d = 2) {
  return n.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
}

function fmtVol(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

export default function StockDetailPage({ params }: { params: { symbol: string } }) {
  const { symbol } = params;
  const { t } = useLang();
  const [period, setPeriod] = useState<Period>("1d");
  const [tab, setTab] = useState<Tab>("overview");

  const { data, error, isLoading } = useSWR(
    `stock-${symbol}`,
    () => api.stockDetail(symbol),
    { refreshInterval: 60_000 }
  );

  const { data: wsData, connected } = useWebSocket(symbol);

  const { data: candles } = useSWR(
    `candles-${symbol}-${period}`,
    () => api.stockCandles(symbol, period, PERIOD_INTERVAL[period]),
    { refreshInterval: 60_000 }
  );

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 bg-surface rounded animate-pulse w-40" />
        <div className="h-12 bg-surface rounded animate-pulse w-64" />
        <div className="h-96 bg-surface rounded animate-pulse" />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-48 bg-surface rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-20">
        <p className="text-bear text-xl mb-2">{t("detail.not_found")}: {symbol}</p>
        <Link href="/" className="text-accent text-sm hover:underline">{t("detail.back")}</Link>
      </div>
    );
  }

  const livePrice = wsData?.price ?? data.price;
  const liveChange = wsData?.change ?? data.change;
  const liveChangePct = wsData?.change_pct ?? data.change_pct;
  const positive = liveChange >= 0;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-4">
        <Link href="/" className="text-neutral text-sm hover:text-white transition">{t("detail.back")}</Link>
      </div>

      {/* Stock header */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-white">{displaySymbol(symbol)}</h1>
            {connected && (
              <span className="flex items-center gap-1 text-xs text-neutral">
                <span className="w-1.5 h-1.5 rounded-full bg-bull animate-pulse" />
                {t("detail.live")}
              </span>
            )}
          </div>
          <p className="text-neutral text-sm mt-0.5">{data.name}</p>
        </div>
        <div className="text-right">
          <div className="text-4xl font-mono font-bold text-white">${fmt(livePrice)}</div>
          <div className={clsx("text-lg font-mono mt-1", positive ? "text-bull" : "text-bear")}>
            {positive ? "+" : ""}{fmt(liveChange)} ({positive ? "+" : ""}{fmt(liveChangePct)}%)
          </div>
        </div>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {[
          { label: t("detail.volume"), value: fmtVol(wsData?.volume ?? data.volume) },
          { label: t("detail.avg_volume"), value: fmtVol(data.avg_volume) },
          { label: t("detail.vol_ratio"), value: `${fmt(data.volume_ratio, 1)}x` },
          { label: t("detail.market_cap"), value: data.market_cap ? `$${(data.market_cap / 1e9).toFixed(1)}B` : "—" },
        ].map((s) => (
          <div key={s.label} className="bg-surface border border-border rounded p-3">
            <div className="text-xs text-neutral">{s.label}</div>
            <div className="font-mono font-semibold text-white mt-0.5">{s.value}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-5 border-b border-border">
        {(["overview", "news"] as Tab[]).map((tabKey) => (
          <button
            key={tabKey}
            onClick={() => setTab(tabKey)}
            className={clsx(
              "px-5 py-2 text-sm font-semibold border-b-2 -mb-px transition",
              tab === tabKey
                ? "border-accent text-accent"
                : "border-transparent text-neutral hover:text-white"
            )}
          >
            {tabKey === "overview" ? t("detail.tab_overview") : (
              <>
                {t("detail.tab_news")}
                <span className="ml-1.5 text-xs opacity-60">({data.news.length})</span>
              </>
            )}
          </button>
        ))}
      </div>

      {/* Overview tab */}
      {tab === "overview" && (
        <>
          {/* Chart period selector */}
          <div className="flex gap-2 mb-3">
            {(["1d", "5d", "1mo", "3mo"] as Period[]).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={clsx(
                  "px-3 py-1 rounded text-xs font-semibold border transition",
                  period === p
                    ? "bg-accent/20 text-accent border-accent/50"
                    : "border-border text-neutral hover:text-white"
                )}
              >
                {p}
              </button>
            ))}
          </div>

          {/* Chart */}
          {(candles || data.candles).length > 0 && (
            <div className="mb-6">
              <TradingChart
                candles={candles || data.candles}
                technical={data.technical}
                entry={data.trade_setup.entry}
                target={data.trade_setup.target}
                stopLoss={data.trade_setup.stop_loss}
              />
            </div>
          )}

          {/* Analysis cards */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <TradeSetupCard
              setup={data.trade_setup}
              technical={data.technical}
              currentPrice={livePrice}
            />
            <ProbabilityMeter setup={data.trade_setup} />

            {/* Technical indicators */}
            <div className="bg-surface border border-border rounded-lg p-5">
              <h3 className="text-sm font-semibold text-neutral mb-4">{t("detail.tech_title")}</h3>
              <div className="space-y-0">
                {[
                  {
                    label: t("detail.trend"),
                    value: data.technical.trend.toUpperCase(),
                    color: data.technical.trend === "bullish" ? "text-bull" :
                           data.technical.trend === "bearish" ? "text-bear" : "text-neutral",
                  },
                  { label: t("detail.rsi"), value: data.technical.rsi ? fmt(data.technical.rsi, 1) : "—",
                    color: data.technical.rsi && data.technical.rsi < 30 ? "text-bull" :
                           data.technical.rsi && data.technical.rsi > 70 ? "text-bear" : "text-white" },
                  { label: t("detail.ma20"), value: data.technical.ma20 ? `$${fmt(data.technical.ma20)}` : "—", color: "text-white" },
                  { label: t("detail.ma50"), value: data.technical.ma50 ? `$${fmt(data.technical.ma50)}` : "—", color: "text-white" },
                  { label: t("detail.atr"), value: data.technical.atr ? `$${fmt(data.technical.atr)}` : "—", color: "text-white" },
                  { label: t("detail.bb_upper"), value: data.technical.bb_upper ? `$${fmt(data.technical.bb_upper)}` : "—", color: "text-bear" },
                  { label: t("detail.bb_lower"), value: data.technical.bb_lower ? `$${fmt(data.technical.bb_lower)}` : "—", color: "text-bull" },
                ].map((row) => (
                  <div key={row.label} className="flex justify-between text-sm border-b border-border py-2 last:border-0">
                    <span className="text-neutral">{row.label}</span>
                    <span className={clsx("font-mono font-semibold", row.color)}>{row.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}

      {/* News tab */}
      {tab === "news" && (
        <div className="max-w-3xl">
          <NewsFeed news={data.news} symbol={symbol} />
        </div>
      )}

      <p className="text-center text-[11px] text-neutral mt-8">{t("detail.disclaimer")}</p>
    </div>
  );
}
