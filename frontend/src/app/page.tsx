"use client";
import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { useLang } from "@/lib/context/LanguageContext";
import StockCard from "@/components/StockCard";
import type { Market, Sentiment, StockSummary } from "@/lib/types";
import { MARKET_INFO } from "@/lib/types";

type Filter = "all" | Sentiment;

const MARKETS: Market[] = ["us", "th", "cn"];

export default function DashboardPage() {
  const { t } = useLang();
  const [market, setMarket] = useState<Market>("us");
  const [filter, setFilter] = useState<Filter>("all");

  const { data, error, isLoading } = useSWR(
    `screener-today-${market}`,
    () => api.screenerToday(market),
    { refreshInterval: 60_000 }
  );

  const filterOptions: { key: Filter; label: () => string }[] = [
    { key: "all", label: () => t("dash.filter_all") },
    { key: "bullish", label: () => t("dash.filter_bullish") },
    { key: "bearish", label: () => t("dash.filter_bearish") },
    { key: "neutral", label: () => t("dash.filter_neutral") },
  ];

  const filtered: StockSummary[] = (data || []).filter((s) =>
    filter === "all" ? true : s.signal === filter
  );

  return (
    <div>
      {/* Header */}
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-white mb-1">{t("dash.title")}</h1>
        <p className="text-sm text-neutral">{t("dash.subtitle")}</p>
      </div>

      {/* Market tabs */}
      <div className="flex gap-1 mb-5 bg-surface border border-border rounded-lg p-1 w-fit">
        {MARKETS.map((id) => (
          <button
            key={id}
            onClick={() => { setMarket(id); setFilter("all"); }}
            className={`px-4 py-1.5 rounded-md text-xl transition ${
              market === id
                ? "bg-accent/20 shadow"
                : "opacity-40 hover:opacity-70"
            }`}
            title={MARKET_INFO[id].labelEn}
          >
            {MARKET_INFO[id].flag}
          </button>
        ))}
      </div>

      {/* Rank legend */}
      <div className="flex items-center gap-3 mb-4 text-xs text-neutral">
        <span className="font-semibold text-white">{t("dash.rank_label")}:</span>
        {[1, 2, 3, 4, 5].map((r) => (
          <span key={r} className="flex items-center gap-1">
            <RankBadge rank={r} />
            {r === 1 && <span className="text-neutral">อ่อน</span>}
            {r === 5 && <span className="text-yellow-400">ซิ่ง 🔥</span>}
          </span>
        ))}
        <span className="text-neutral ml-1">— {t("dash.rank_tooltip")}</span>
      </div>

      {/* Signal filter tabs */}
      <div className="flex gap-2 mb-5 flex-wrap">
        {filterOptions.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`px-4 py-1.5 rounded-full text-sm font-semibold border transition ${
              filter === key
                ? key === "bullish"
                  ? "bg-bull/20 text-bull border-bull/50"
                  : key === "bearish"
                  ? "bg-bear/20 text-bear border-bear/50"
                  : "bg-accent/20 text-accent border-accent/50"
                : "border-border text-neutral hover:text-white"
            }`}
          >
            {label()}
            {data && key !== "all" && (
              <span className="ml-1.5 text-xs opacity-70">
                ({data.filter((s) => s.signal === key).length})
              </span>
            )}
          </button>
        ))}

        <div className="ml-auto flex items-center gap-2 text-xs text-neutral">
          <span className="w-1.5 h-1.5 rounded-full bg-bull animate-pulse" />
          {t("nav.live_delay")}
        </div>
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-surface border border-border rounded-lg h-56 animate-pulse" />
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="text-center py-20">
          <p className="text-bear text-lg mb-2">{t("dash.loading_error")}</p>
          <p className="text-neutral text-sm">{t("dash.backend_hint")}</p>
        </div>
      )}

      {/* Empty */}
      {data && !filtered.length && (
        <div className="text-center py-20 text-neutral">{t("dash.no_signals")}</div>
      )}

      {/* Stock grid — sorted by momentum_rank desc */}
      {filtered.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...filtered]
            .sort((a, b) => b.momentum_rank - a.momentum_rank)
            .map((stock) => (
              <StockCard key={stock.symbol} stock={stock} />
            ))}
        </div>
      )}

      <p className="text-center text-[11px] text-neutral mt-10">{t("dash.disclaimer")}</p>
    </div>
  );
}

// Exported so StockCard can reuse
export function RankBadge({ rank, size = "md" }: { rank: number; size?: "sm" | "md" }) {
  const cfg: Record<number, { bg: string; text: string; label: string }> = {
    1: { bg: "bg-neutral/20", text: "text-neutral", label: "1" },
    2: { bg: "bg-blue-900/40", text: "text-blue-400", label: "2" },
    3: { bg: "bg-yellow-900/40", text: "text-yellow-400", label: "3" },
    4: { bg: "bg-orange-900/40", text: "text-orange-400", label: "4" },
    5: { bg: "bg-red-900/40", text: "text-red-400", label: "5" },
  };
  const { bg, text, label } = cfg[rank] ?? cfg[1];
  const sizeClass = size === "sm" ? "w-4 h-4 text-[9px]" : "w-6 h-6 text-xs";
  return (
    <span className={`inline-flex items-center justify-center rounded-full font-bold shrink-0 ${sizeClass} ${bg} ${text}`}>
      {label}
    </span>
  );
}
