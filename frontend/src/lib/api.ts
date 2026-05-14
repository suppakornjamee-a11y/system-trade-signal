import type { StockDetail, StockSummary, CandleBar, PaperTradingSummary } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

export const api = {
  screenerToday: (market = "us") => fetchJson<StockSummary[]>(`/api/screener/today?market=${market}`),
  stockDetail: (symbol: string) =>
    fetchJson<StockDetail>(`/api/stocks/${symbol}`),
  stockCandles: (symbol: string, period = "1d", interval = "5m") =>
    fetchJson<CandleBar[]>(
      `/api/stocks/${symbol}/candles?period=${period}&interval=${interval}`
    ),
  stockQuote: (symbol: string) =>
    fetchJson<{ price: number; change: number; change_pct: number }>(
      `/api/stocks/${symbol}/quote`
    ),
  summarizeNews: (url: string, title: string, symbol: string, lang: string) =>
    fetchJson<{ summary: string }>(
      `/api/news/summarize?url=${encodeURIComponent(url)}&title=${encodeURIComponent(title)}&symbol=${encodeURIComponent(symbol)}&lang=${lang}`
    ),
  translateTitle: (title: string) =>
    fetchJson<{ title: string }>(
      `/api/news/translate?title=${encodeURIComponent(title)}`
    ),
  paperTradingSummary: (market = "us") =>
    fetchJson<PaperTradingSummary>(`/api/paper-trading/summary?market=${market}`),
};
