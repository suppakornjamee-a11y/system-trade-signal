"use client";
import { useState, useEffect } from "react";
import type { NewsItem } from "@/lib/types";
import { useLang } from "@/lib/context/LanguageContext";
import { api } from "@/lib/api";
import { clsx } from "clsx";

const SENTIMENT_COLOR = {
  bullish: "text-bull bg-bull/10 border-bull/30",
  bearish: "text-bear bg-bear/10 border-bear/30",
  neutral: "text-neutral bg-neutral/10 border-neutral/30",
};

function timeAgo(ts: number | string) {
  let ms: number;
  if (typeof ts === "string") {
    ms = new Date(ts).getTime();
  } else {
    ms = ts < 1e12 ? ts * 1000 : ts;
  }
  const diff = Date.now() - ms;
  const h = Math.floor(diff / 3600000);
  const m = Math.floor(diff / 60000);
  if (h > 24) return `${Math.floor(h / 24)}d ago`;
  if (h > 0) return `${h}h ago`;
  return `${m}m ago`;
}

function NewsArticle({
  item,
  symbol,
}: {
  item: NewsItem;
  symbol: string;
}) {
  const { t, lang } = useLang();
  const [summary, setSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [translatedTitle, setTranslatedTitle] = useState<string | null>(null);
  const [translating, setTranslating] = useState(false);

  useEffect(() => {
    if (lang !== "th" || !item.title || translatedTitle) return;
    let cancelled = false;
    setTranslating(true);
    api.translateTitle(item.title)
      .then((res) => { if (!cancelled) setTranslatedTitle(res.title); })
      .catch((err) => { console.error("[translate]", err); })
      .finally(() => { if (!cancelled) setTranslating(false); });
    return () => { cancelled = true; };
  }, [lang, item.title, translatedTitle]);

  const sentimentLabel =
    item.sentiment === "bullish"
      ? t("news.bullish")
      : item.sentiment === "bearish"
      ? t("news.bearish")
      : t("news.neutral");

  const handleSummarize = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (summary || loading || !item.link) return;

    setLoading(true);
    setError(null);
    try {
      const res = await api.summarizeNews(item.link, item.title, symbol, lang);
      setSummary(res.summary);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("503") || msg.includes("API_KEY")) {
        setError(t("news.no_api_key"));
      } else {
        setError(t("news.summary_error"));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-border/50 hover:border-border transition bg-bg/30">
      {/* Article header — clickable link */}
      <a
        href={item.link}
        target="_blank"
        rel="noopener noreferrer"
        className="block p-3 hover:bg-bg/60 transition rounded-t-lg"
      >
        <div className="flex items-start gap-2 mb-1.5">
          <span className={clsx(
            "text-[10px] font-bold px-1.5 py-0.5 rounded border shrink-0 mt-0.5",
            SENTIMENT_COLOR[item.sentiment]
          )}>
            {sentimentLabel}
          </span>
          <span className="text-sm text-white leading-snug">
            {translating
              ? <span className="opacity-50">{item.title}<span className="animate-pulse"> …</span></span>
              : (translatedTitle ?? item.title)
            }
          </span>
        </div>
        <div className="flex gap-2 text-[10px] text-neutral ml-0.5">
          <span>{item.publisher}</span>
          <span>·</span>
          <span>{timeAgo(item.published_at)}</span>
        </div>
      </a>

      {/* Summary section */}
      <div className="px-3 pb-3">
        {!summary && !loading && !error && item.link && (
          <button
            onClick={handleSummarize}
            className="flex items-center gap-1.5 text-xs text-accent hover:text-accent/80 transition mt-1"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
            {t("news.summarize_btn")}
          </button>
        )}

        {loading && (
          <div className="flex items-center gap-2 text-xs text-neutral mt-1">
            <div className="w-3 h-3 border border-accent border-t-transparent rounded-full animate-spin" />
            {t("news.summarizing")}
          </div>
        )}

        {error && (
          <p className="text-xs text-bear mt-1">{error}</p>
        )}

        {summary && (
          <div className="mt-2 rounded-md bg-accent/5 border border-accent/20 p-3">
            <div className="flex items-center gap-1.5 text-[10px] text-accent font-semibold mb-1.5">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                />
              </svg>
              {t("news.summary_label")}
            </div>
            <p className="text-xs text-white/90 leading-relaxed">{summary}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function NewsFeed({ news, symbol }: { news: NewsItem[]; symbol?: string }) {
  const { t } = useLang();

  if (!news.length) {
    return (
      <div className="bg-surface border border-border rounded-lg p-5">
        <h3 className="text-sm font-semibold text-neutral mb-2">{t("news.title")}</h3>
        <p className="text-xs text-neutral">{t("news.no_news")}</p>
      </div>
    );
  }

  const bullCount = news.filter((n) => n.sentiment === "bullish").length;
  const bearCount = news.filter((n) => n.sentiment === "bearish").length;
  const neutralCount = news.filter((n) => n.sentiment === "neutral").length;

  return (
    <div className="bg-surface border border-border rounded-lg p-5">
      {/* Header with breakdown */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-neutral">{t("news.title")}</h3>
        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1 text-bull">
            <span className="w-2 h-2 rounded-full bg-bull inline-block" />
            {bullCount} {t("news.bullish")}
          </span>
          <span className="flex items-center gap-1 text-neutral">
            <span className="w-2 h-2 rounded-full bg-neutral inline-block" />
            {neutralCount} {t("news.neutral")}
          </span>
          <span className="flex items-center gap-1 text-bear">
            <span className="w-2 h-2 rounded-full bg-bear inline-block" />
            {bearCount} {t("news.bearish")}
          </span>
        </div>
      </div>

      {/* Breakdown bar */}
      <div className="flex h-1.5 rounded-full overflow-hidden mb-4">
        {bullCount > 0 && (
          <div className="bg-bull" style={{ width: `${(bullCount / news.length) * 100}%` }} />
        )}
        {neutralCount > 0 && (
          <div className="bg-neutral/50" style={{ width: `${(neutralCount / news.length) * 100}%` }} />
        )}
        {bearCount > 0 && (
          <div className="bg-bear" style={{ width: `${(bearCount / news.length) * 100}%` }} />
        )}
      </div>

      <div className="space-y-2">
        {news.map((item, i) => (
          <NewsArticle key={i} item={item} symbol={symbol ?? ""} />
        ))}
      </div>
    </div>
  );
}
