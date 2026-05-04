import type { Market } from "./types";

/** Strip market suffix for display: "PTT.BK" → "PTT", "0700.HK" → "0700" */
export function displaySymbol(symbol: string): string {
  return symbol.replace(/\.(BK|HK|SS|SZ)$/i, "");
}

// TH: map display symbol → company domain
const TH_DOMAINS: Record<string, string> = {
  PTT: "pttplc.com",
  SCB: "scb.co.th",
  KBANK: "kasikornbank.com",
  BBL: "bangkokbank.com",
  KTB: "ktb.co.th",
  AOT: "airportthai.co.th",
  ADVANC: "ais.th",
  CPALL: "cpall.co.th",
  TRUE: "true.th",
  MINT: "minor.com",
  CPN: "cpn.co.th",
  GULF: "gulf.co.th",
  GPSC: "gpsc.co.th",
  DELTA: "deltathailand.com",
  BDMS: "bdms.co.th",
  SCC: "scg.co.th",
  IVL: "indoramaventures.com",
  PTTGC: "pttgcgroup.com",
  TOP: "thaioilgroup.com",
  OSP: "osp.co.th",
  HANA: "hana.co.th",
  BH: "bumrungrad.com",
  CPAXT: "cpaxtra.co.th",
  SPRC: "srpcth.com",
};

// CN A-shares: map display ticker → company domain
const CN_DOMAINS: Record<string, string> = {
  "600519": "moutai.com.cn",
  "600036": "cmbchina.com",
  "601318": "pingan.com",
  "300750": "catl.com",
  "002594": "byd.com",
  "601857": "petrochina.com.cn",
  "600941": "10086.cn",
  "601398": "icbc.com.cn",
  "600900": "ctgpc.com.cn",
  "601012": "longi.com",
  "002415": "hikvision.com",
  "600030": "cs.ecitic.com",
  "601088": "shenhuagroup.com.cn",
  "000858": "wuliangye-y.com",
  "600309": "wanhuachem.com",
};

function googleFavicon(domain: string): string {
  return `https://www.google.com/s2/favicons?domain=${domain}&sz=64`;
}

/** Returns the best logo URL for a symbol+market, or "" if unknown (show avatar). */
export function getLogoUrl(symbol: string, market: Market): string {
  const disp = displaySymbol(symbol);

  if (market === "us") {
    // Parqet covers most US large-caps with clean SVG logos
    return `https://assets.parqet.com/logos/symbol/${disp}?format=svg`;
  }

  if (market === "th") {
    const domain = TH_DOMAINS[disp];
    return domain ? googleFavicon(domain) : "";
  }

  if (market === "cn") {
    const domain = CN_DOMAINS[disp];
    if (domain) return googleFavicon(domain);
    return "";
  }

  return "";
}

/** Deterministic background color from symbol string */
export function symbolColor(symbol: string): string {
  const COLORS = [
    "bg-blue-700", "bg-purple-700", "bg-teal-700",
    "bg-indigo-700", "bg-rose-700", "bg-amber-700",
    "bg-cyan-700", "bg-emerald-700",
  ];
  let hash = 0;
  for (const ch of symbol) hash = (hash * 31 + ch.charCodeAt(0)) & 0xffff;
  return COLORS[hash % COLORS.length];
}
