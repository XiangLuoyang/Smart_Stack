import { useEffect } from "react";
import { useStore } from "../stores/useStore";

/**
 * 订阅后端 SSE 行情流,自动写入 store.quotes。
 * 断线 3 秒后自动重连。
 */
export function useQuoteStream() {
  const watchlist = useStore((s) => s.watchlist);
  const setQuotes = useStore((s) => s.setQuotes);

  useEffect(() => {
    if (watchlist.length === 0) return;
    const symbols = watchlist.join(",");
    let es: EventSource | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let stopped = false;

    const connect = () => {
      es = new EventSource(`/api/market/stream?symbols=${encodeURIComponent(symbols)}`);
      es.onmessage = (ev) => {
        try {
          const arr = JSON.parse(ev.data) as Array<{
            symbol: string;
            price: number;
            ts: string;
          }>;
          const now = new Date().toISOString();
          setQuotes(
            arr.map((x) => ({
              symbol: x.symbol,
              price: x.price,
              ts: x.ts || now,
            })) as any
          );
        } catch {
          /* 忽略心跳/格式异常 */
        }
      };
      es.onerror = () => {
        es?.close();
        if (!stopped) reconnectTimer = setTimeout(connect, 3000);
      };
    };

    connect();
    return () => {
      stopped = true;
      es?.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, [watchlist.join(","), setQuotes]);
}
