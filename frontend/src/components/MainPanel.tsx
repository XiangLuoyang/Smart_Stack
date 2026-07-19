import { Button, Spin, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { useStore } from "../stores/useStore";
import { getKline } from "../api/client";
import KlineChart from "./KlineChart";
import OrderEntryForm from "./OrderEntryForm";
import type { KlineBar } from "../types";

const { Text } = Typography;

export default function MainPanel() {
  const currentSymbol = useStore((s) => s.currentSymbol);
  const currentQuote = useStore((s) =>
    s.currentSymbol ? s.quotes[s.currentSymbol] : null
  );
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
  const changeColor =
    change == null ? "#666" : change > 0 ? "#f5222d" : change < 0 ? "#52c41a" : "#666";

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: "#1e1e2d" }}>
      {/* 标的头部 */}
      <div style={{ padding: "6px 12px", display: "flex", alignItems: "center", gap: 16, background: "#1e1e2d" }}>
        <Text strong style={{ color: "#fff", fontSize: 18 }}>{currentSymbol ?? "未选择标的"}</Text>
        {currentQuote && (
          <>
            <Text style={{ color: changeColor, fontSize: 18, fontWeight: 600 }}>
              {currentQuote.price.toFixed(2)}
            </Text>
            {change != null && (
              <Tag color={change > 0 ? "red" : change < 0 ? "green" : "default"}>
                {change >= 0 ? "+" : ""}{change.toFixed(2)}%
              </Tag>
            )}
          </>
        )}
        <div style={{ marginLeft: "auto" }}>
          <Tag.CheckableTag checked={days === 60} onChange={() => setDays(60)}>60d</Tag.CheckableTag>
          <Tag.CheckableTag checked={days === 120} onChange={() => setDays(120)}>120d</Tag.CheckableTag>
          <Tag.CheckableTag checked={days === 250} onChange={() => setDays(250)}>250d</Tag.CheckableTag>
        </div>
      </div>

      <div style={{ flex: 1, position: "relative", minHeight: 300 }}>
        {loading ? (
          <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Spin />
          </div>
        ) : bars.length > 0 ? (
          <KlineChart bars={bars} />
        ) : (
          <div style={{
            position: "absolute", inset: 0, display: "flex",
            alignItems: "center", justifyContent: "center", color: "#888"
          }}>
            {currentSymbol ? "加载中或无数据" : "请从左侧选择标的"}
          </div>
        )}
      </div>

      <OrderEntryForm />
    </div>
  );
}
