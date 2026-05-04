"use client";
import type { TradeSetup, TechnicalData } from "@/lib/types";
import { useLang } from "@/lib/context/LanguageContext";
import { clsx } from "clsx";

function fmt(n: number, d = 2) {
  return n.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
}

function Row({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-border last:border-0">
      <span className="text-sm text-neutral">{label}</span>
      <span className={clsx("text-sm font-mono font-semibold", color || "text-white")}>{value}</span>
    </div>
  );
}

export default function TradeSetupCard({
  setup,
  technical,
  currentPrice,
}: {
  setup: TradeSetup;
  technical: TechnicalData;
  currentPrice: number;
}) {
  const { t } = useLang();
  const isLong = setup.direction === "long";
  const pnlAtTarget = isLong
    ? ((setup.target - setup.entry) / setup.entry) * 100
    : ((setup.entry - setup.target) / setup.entry) * 100;
  const pnlAtStop = isLong
    ? ((setup.stop_loss - setup.entry) / setup.entry) * 100
    : ((setup.entry - setup.stop_loss) / setup.entry) * 100;

  const rsiLabel =
    technical.rsi && technical.rsi < 30
      ? t("setup.oversold")
      : technical.rsi && technical.rsi > 70
      ? t("setup.overbought")
      : t("setup.neutral");

  return (
    <div className="bg-surface border border-border rounded-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-neutral">{t("setup.title")}</h3>
        <span className={clsx(
          "text-xs font-bold px-3 py-1 rounded-full",
          isLong ? "bg-bull/20 text-bull" : "bg-bear/20 text-bear"
        )}>
          {isLong ? t("setup.long") : t("setup.short")}
        </span>
      </div>

      <div className="mb-4">
        <Row label={t("setup.entry_price")} value={`$${fmt(setup.entry)}`} />
        <Row
          label={t("setup.target_price")}
          value={`$${fmt(setup.target)} (+${fmt(pnlAtTarget)}%)`}
          color="text-bull"
        />
        <Row
          label={t("setup.stop_loss")}
          value={`$${fmt(setup.stop_loss)} (${fmt(pnlAtStop)}%)`}
          color="text-bear"
        />
        <Row label={t("setup.rr")} value={`${setup.risk_reward}x`} color="text-accent" />
      </div>

      {/* Price level bar */}
      <div className="mb-4">
        <div className="text-xs text-neutral mb-2">{t("setup.price_levels")}</div>
        <div className="relative h-2 bg-bg rounded-full">
          {(() => {
            const lo = Math.min(setup.stop_loss, setup.target, currentPrice) * 0.995;
            const hi = Math.max(setup.stop_loss, setup.target, currentPrice) * 1.005;
            const range = hi - lo;
            const pos = (v: number) => `${((v - lo) / range) * 100}%`;
            return (
              <>
                <div className="absolute -top-5 text-[10px] text-bull" style={{ left: pos(setup.target), transform: "translateX(-50%)" }}>T</div>
                <div className="absolute w-2 h-2 rounded-full bg-bull" style={{ left: pos(setup.target), transform: "translateX(-50%)" }} />
                <div className="absolute -top-5 text-[10px] text-accent" style={{ left: pos(setup.entry), transform: "translateX(-50%)" }}>E</div>
                <div className="absolute w-2 h-2 rounded-full bg-accent" style={{ left: pos(setup.entry), transform: "translateX(-50%)" }} />
                <div className="absolute w-1 h-4 -top-1 bg-white/60 rounded" style={{ left: pos(currentPrice), transform: "translateX(-50%)" }} />
                <div className="absolute -top-5 text-[10px] text-bear" style={{ left: pos(setup.stop_loss), transform: "translateX(-50%)" }}>SL</div>
                <div className="absolute w-2 h-2 rounded-full bg-bear" style={{ left: pos(setup.stop_loss), transform: "translateX(-50%)" }} />
              </>
            );
          })()}
        </div>
        <div className="flex justify-between text-[10px] text-neutral mt-3">
          <span>SL ${fmt(setup.stop_loss)}</span>
          <span className="text-white">${fmt(currentPrice)}</span>
          <span>T ${fmt(setup.target)}</span>
        </div>
      </div>

      {/* Technical indicators */}
      <div className="border-t border-border pt-3 grid grid-cols-3 gap-3">
        {technical.rsi !== null && (
          <div className="text-center">
            <div className="text-xs text-neutral">RSI</div>
            <div className={clsx("font-mono font-bold text-sm",
              technical.rsi < 30 ? "text-bull" : technical.rsi > 70 ? "text-bear" : "text-white"
            )}>
              {fmt(technical.rsi, 1)}
            </div>
            <div className="text-[10px] text-neutral">{rsiLabel}</div>
          </div>
        )}
        <div className="text-center">
          <div className="text-xs text-neutral">Support</div>
          <div className="font-mono font-bold text-sm text-bull">${fmt(technical.support)}</div>
        </div>
        <div className="text-center">
          <div className="text-xs text-neutral">Resistance</div>
          <div className="font-mono font-bold text-sm text-bear">${fmt(technical.resistance)}</div>
        </div>
      </div>
    </div>
  );
}
