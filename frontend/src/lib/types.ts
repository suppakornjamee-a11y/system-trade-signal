export type Sentiment = "bullish" | "bearish" | "neutral";
export type Direction = "long" | "short";
export type Market = "us" | "th" | "cn";

export const MARKET_CURRENCY: Record<Market, string> = {
  us: "$",
  th: "฿",
  cn: "HK$",
};

export const MARKET_INFO: Record<Market, { flag: string; labelTh: string; labelEn: string }> = {
  us: { flag: "🇺🇸", labelTh: "สหรัฐ", labelEn: "US" },
  th: { flag: "🇹🇭", labelTh: "ไทย", labelEn: "Thailand" },
  cn: { flag: "🇨🇳", labelTh: "จีน", labelEn: "China" },
};

export interface NewsItem {
  title: string;
  publisher: string;
  link: string;
  published_at: number;
  sentiment: Sentiment;
}

export interface TechnicalData {
  rsi: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_hist: number | null;
  ma20: number | null;
  ma50: number | null;
  bb_upper: number | null;
  bb_lower: number | null;
  atr: number | null;
  support: number;
  resistance: number;
  trend: Sentiment;
}

export interface TradeSetup {
  direction: Direction;
  entry: number;
  target: number;
  stop_loss: number;
  risk_reward: number;
  probability_pct: number;
  tech_score: number;
  news_score: number;
  volume_score: number;
}

export interface StockSummary {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  avg_volume: number;
  volume_ratio: number;
  market_cap: number | null;
  news_sentiment: Sentiment;
  news_count: number;
  signal: Sentiment;
  trade_setup: TradeSetup;
  momentum_rank: number;  // 1-5
  market: Market;
}

export interface CandleBar {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface StockDetail {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  avg_volume: number;
  volume_ratio: number;
  market_cap: number | null;
  technical: TechnicalData;
  trade_setup: TradeSetup;
  news: NewsItem[];
  candles: CandleBar[];
}

export interface PriceUpdate {
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  timestamp: number;
}
