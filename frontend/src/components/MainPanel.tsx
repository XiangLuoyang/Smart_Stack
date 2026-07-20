import { Segmented, Spin, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { useStore } from "../stores/useStore";
import { getKline } from "../api/client";
import KlineChart from "./KlineChart";
import OrderEntryForm from "./OrderEntryForm";
import SymbolTag from "./SymbolTag";
import type { KlineBar } from "../types";

const { Text } = Typography;

export default function MainPanel() {
  const currentSymbol = useStore((s) => s.currentSymbol);
  const currentQuote = useStore((s) => (s.currentSymbol ? s.quotes[s.currentSymbol] : null));
  const [bars, setBars] = useState<KlineBar[]>([]);
  const [loading, setLoading] = useState(false);
  const [days, setDays] = useState(120);

  useEffect(() => {
    if (!currentSymbol) {
      setBars([]);
      return;
    }
    setLoading(true);
    getKline(currentSymbol, days)
      .then(setBars)
      .catch(() => setBars([]))
      .finally(() => setLoading(false));
  }, [currentSymbol, days]);

  const change = currentQuote?.change_pct;
  const changeColor = change == null ? "#6e7681" : change > 0 ? "#ef5350" : change < 0 ? "#26a69a" : "#6e7681";

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: "#0b0e14" }}>
      <div
        style={{
          padding: "6px 14px",
          display: "flex",
          alignItems: "center",
          gap: 14,
          background: "#0b0e14",
          borderBottom: "1px solid #21262d",
        }}
      >
        {currentSymbol ? (
          <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
            <SymbolTag code={currentSymbol} strongName />
            <Text style={{ color: "#6e7681", fontSize: 12 }}>{currentSymbol}</Text>
          </div>
        ) : (
          <Text style={{ color: "#6e7681" }}>未选择标的</Text>
        )}
        {currentQuote && (
          <>
            <Text style={{ color: changeColor, fontSize: 20, fontWeight: 700, fontFamily: "ui-monospace, monospace" }}>
              {currentQuote.price.toFixed(2)}
            </Text>
            {change != null && (
              <Tag color={change > 0 ? "red" : change < 0 ? "green" : "default"} style={{ fontSize: 12 }}>
                {change >= 0 ? "+" : ""}
                {change.toFixed(2)}%
              </Tag>
            )}
          </>
        )}
        <div style={{ marginLeft: "auto" }}>
          <Segmented
            size="small"
            value={days}
            onChange={(v) => setDays(v as number)}
            options={[
              { label: "60d", value: 60 },
              { label: "120d", value: 120 },
              { label: "250d", value: 250 },
            ]}
          />
        </div>
      </div>

      <div style={{ flex: 1, position: "relative", minHeight: 300 }}>
        {loading ? (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Spin />
          </div>
        ) : bars.length > 0 ? (
          <KlineChart bars={bars} />
        ) : (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#6e7681",
            }}
          >
            {currentSymbol ? "加载中或无数据" : "请从左侧选择标的"}
          </div>
        )}
      </div>

      <OrderEntryForm />
    </div>
  );
}