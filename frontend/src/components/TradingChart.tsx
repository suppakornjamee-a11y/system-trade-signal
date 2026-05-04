"use client";
import { useEffect, useRef } from "react";
import type { CandleBar, TechnicalData } from "@/lib/types";

interface Props {
  candles: CandleBar[];
  technical: TechnicalData;
  entry: number;
  target: number;
  stopLoss: number;
}

export default function TradingChart({ candles, technical, entry, target, stopLoss }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || !candles.length) return;

    let chart: import("lightweight-charts").IChartApi | null = null;

    import("lightweight-charts").then(({ createChart, CrosshairMode, LineStyle }) => {
      if (!containerRef.current) return;

      chart = createChart(containerRef.current, {
        layout: {
          background: { color: "#0d1117" },
          textColor: "#8b949e",
        },
        grid: {
          vertLines: { color: "#21262d" },
          horzLines: { color: "#21262d" },
        },
        crosshair: { mode: CrosshairMode.Normal },
        rightPriceScale: { borderColor: "#30363d" },
        timeScale: { borderColor: "#30363d", timeVisible: true, secondsVisible: false },
        width: containerRef.current.clientWidth,
        height: 400,
      });

      // Candlestick series
      const candleSeries = chart.addCandlestickSeries({
        upColor: "#26a641",
        downColor: "#f85149",
        borderUpColor: "#26a641",
        borderDownColor: "#f85149",
        wickUpColor: "#26a641",
        wickDownColor: "#f85149",
      });

      const chartData = candles.map((c) => ({
        time: c.time as import("lightweight-charts").Time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }));
      candleSeries.setData(chartData);

      // Entry line
      candleSeries.createPriceLine({
        price: entry,
        color: "#58a6ff",
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: "Entry",
      });

      // Target line
      candleSeries.createPriceLine({
        price: target,
        color: "#26a641",
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: "Target",
      });

      // Stop loss line
      candleSeries.createPriceLine({
        price: stopLoss,
        color: "#f85149",
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: "Stop Loss",
      });

      // Support line
      if (technical.support) {
        candleSeries.createPriceLine({
          price: technical.support,
          color: "#3fb950",
          lineWidth: 1,
          lineStyle: LineStyle.Dotted,
          axisLabelVisible: false,
          title: "Support",
        });
      }

      // Resistance line
      if (technical.resistance) {
        candleSeries.createPriceLine({
          price: technical.resistance,
          color: "#f85149",
          lineWidth: 1,
          lineStyle: LineStyle.Dotted,
          axisLabelVisible: false,
          title: "Resistance",
        });
      }

      chart.timeScale().fitContent();

      // Volume series
      const volSeries = chart.addHistogramSeries({
        color: "#58a6ff40",
        priceFormat: { type: "volume" },
        priceScaleId: "vol",
      });
      chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
      volSeries.setData(
        candles.map((c) => ({
          time: c.time as import("lightweight-charts").Time,
          value: c.volume,
          color: c.close >= c.open ? "#26a64140" : "#f8514940",
        }))
      );

      // Resize handler
      const onResize = () => {
        if (containerRef.current && chart) {
          chart.applyOptions({ width: containerRef.current.clientWidth });
        }
      };
      window.addEventListener("resize", onResize);
      return () => window.removeEventListener("resize", onResize);
    });

    return () => {
      chart?.remove();
    };
  }, [candles, technical, entry, target, stopLoss]);

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center gap-4 mb-3 text-xs">
        <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-accent inline-block" />Entry</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-bull inline-block" />Target</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-bear inline-block" />Stop Loss</span>
        <span className="flex items-center gap-1.5 text-neutral"><span className="w-3 h-0.5 border-t border-dotted border-neutral inline-block" />S/R Zones</span>
      </div>
      <div ref={containerRef} />
    </div>
  );
}
