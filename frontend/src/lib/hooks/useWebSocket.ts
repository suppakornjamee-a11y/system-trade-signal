"use client";
import { useEffect, useRef, useState } from "react";
import type { PriceUpdate } from "../types";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export function useWebSocket(symbol: string | null) {
  const [data, setData] = useState<PriceUpdate | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!symbol) return;

    const ws = new WebSocket(`${WS_BASE}/ws/${symbol}`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (e) => {
      try {
        const parsed = JSON.parse(e.data);
        if (!parsed.error) setData(parsed as PriceUpdate);
      } catch {}
    };

    return () => {
      ws.close();
      setConnected(false);
    };
  }, [symbol]);

  return { data, connected };
}
