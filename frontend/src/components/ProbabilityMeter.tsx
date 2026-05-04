"use client";
import type { TradeSetup } from "@/lib/types";
import { useLang } from "@/lib/context/LanguageContext";
import { clsx } from "clsx";

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-neutral">{label}</span>
        <span className="text-white font-mono">{value.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 bg-bg rounded-full">
        <div
          className={clsx(
            "h-full rounded-full",
            value >= 60 ? "bg-bull" : value >= 45 ? "bg-yellow-400" : "bg-bear"
          )}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

export default function ProbabilityMeter({ setup }: { setup: TradeSetup }) {
  const { t } = useLang();
  const { probability_pct, tech_score, news_score, volume_score } = setup;

  const color =
    probability_pct >= 60 ? "#26a641" :
    probability_pct >= 50 ? "#d29922" : "#f85149";

  const circumference = 2 * Math.PI * 40;
  const offset = circumference - (probability_pct / 100) * circumference;

  return (
    <div className="bg-surface border border-border rounded-lg p-5">
      <h3 className="text-sm font-semibold text-neutral mb-4">{t("prob.title")}</h3>

      {/* Circular gauge */}
      <div className="flex items-center justify-center mb-4">
        <div className="relative">
          <svg width="100" height="100" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="40" fill="none" stroke="#30363d" strokeWidth="8" />
            <circle
              cx="50" cy="50" r="40" fill="none"
              stroke={color} strokeWidth="8"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              transform="rotate(-90 50 50)"
              style={{ transition: "stroke-dashoffset 0.6s ease" }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold font-mono" style={{ color }}>
              {probability_pct}%
            </span>
            <span className="text-xs text-neutral">{t("prob.win")}</span>
          </div>
        </div>
      </div>

      {/* Score breakdown */}
      <div className="space-y-2">
        <ScoreBar label={t("prob.tech_score")} value={tech_score} />
        <ScoreBar label={t("prob.news_score")} value={news_score} />
        <ScoreBar label={t("prob.vol_score")} value={volume_score} />
      </div>

      <div className="mt-3 pt-3 border-t border-border flex justify-between text-xs text-neutral">
        <span>
          {t("prob.direction")}:{" "}
          <span className={clsx("font-semibold", setup.direction === "long" ? "text-bull" : "text-bear")}>
            {setup.direction === "long" ? t("setup.long") : t("setup.short")}
          </span>
        </span>
        <span>{t("prob.rr")}: <span className="text-white font-mono">{setup.risk_reward}x</span></span>
      </div>
    </div>
  );
}
