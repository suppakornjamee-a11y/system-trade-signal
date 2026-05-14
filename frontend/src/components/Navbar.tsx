"use client";
import Link from "next/link";
import { useState } from "react";
import { useLang } from "@/lib/context/LanguageContext";

export default function Navbar() {
  const { t, lang, setLang } = useLang();
  const [query, setQuery] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      window.location.href = `/stock/${query.trim().toUpperCase()}`;
    }
  };

  return (
    <nav className="border-b border-border bg-surface px-6 py-3 flex items-center justify-between gap-4 flex-wrap">
      <Link href="/" className="text-accent font-bold text-xl tracking-tight shrink-0">
        StockRadar
        <span className="ml-2 text-xs text-neutral font-normal">US Market</span>
      </Link>

      <Link
        href="/paper-trading"
        className="text-sm font-semibold text-neutral hover:text-white transition"
      >
        Paper Trading
      </Link>

      <form onSubmit={handleSearch} className="flex gap-2 flex-1 max-w-sm">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value.toUpperCase())}
          placeholder={t("nav.search_placeholder")}
          className="bg-bg border border-border rounded px-3 py-1.5 text-sm text-white placeholder-neutral focus:outline-none focus:border-accent w-full"
        />
        <button
          type="submit"
          className="bg-accent text-bg px-4 py-1.5 rounded text-sm font-semibold hover:opacity-90 shrink-0"
        >
          {t("nav.search_btn")}
        </button>
      </form>

      <div className="flex items-center gap-3 shrink-0">
        {/* Language toggle */}
        <div className="flex rounded overflow-hidden border border-border text-xs font-semibold">
          <button
            onClick={() => setLang("en")}
            className={`px-3 py-1.5 transition ${
              lang === "en" ? "bg-accent text-bg" : "text-neutral hover:text-white"
            }`}
          >
            EN
          </button>
          <button
            onClick={() => setLang("th")}
            className={`px-3 py-1.5 transition ${
              lang === "th" ? "bg-accent text-bg" : "text-neutral hover:text-white"
            }`}
          >
            TH
          </button>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-bull animate-pulse" />
          <span className="text-xs text-neutral">{t("nav.live_delay")}</span>
        </div>
      </div>
    </nav>
  );
}
