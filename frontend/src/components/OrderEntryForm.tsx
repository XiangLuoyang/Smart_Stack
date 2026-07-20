import { Button, InputNumber, Segmented, Space, message } from "antd";
import { useEffect, useState } from "react";
import { useStore } from "../stores/useStore";
import SymbolTag from "./SymbolTag";

type Side = "BUY" | "SELL";
type OrderType = "MARKET" | "LIMIT";

export default function OrderEntryForm() {
  const currentSymbol = useStore((s) => s.currentSymbol);
  const currentQuote = useStore((s) => (s.currentSymbol ? s.quotes[s.currentSymbol] : null));
  const placeOrder = useStore((s) => s.placeOrder);

  const [side, setSide] = useState<Side>("BUY");
  const [orderType, setOrderType] = useState<OrderType>("LIMIT");
  const [price, setPrice] = useState<number | null>(null);
  const [qty, setQty] = useState<number | null>(100);

  // pre-fill price when symbol changes
  useEffect(() => {
    if (currentQuote) setPrice(currentQuote.price);
  }, [currentSymbol, currentQuote?.price]);

  // hotkeys: F1 buy, F2 sell, Enter submit
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.key === "F1") {
        e.preventDefault();
        setSide("BUY");
      } else if (e.key === "F2") {
        e.preventDefault();
        setSide("SELL");
      } else if (e.key === "Enter") {
        e.preventDefault();
        void submit();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const submit = async () => {
    if (!currentSymbol) {
      message.warning("请先选择标的");
      return;
    }
    if (!qty || qty <= 0) {
      message.warning("数量必须大于 0");
      return;
    }
    if (orderType === "LIMIT" && (!price || price <= 0)) {
      message.warning("限价单请输入价格");
      return;
    }
    try {
      const r = await placeOrder({
        symbol: currentSymbol,
        side,
        qty,
        order_type: orderType,
        price: orderType === "LIMIT" ? price : null,
      });
      if (r?.accepted) {
        message.success(r.message);
      } else {
        message.error(r?.message ?? "下单失败");
      }
    } catch (e: any) {
      message.error("下单异常:" + (e?.response?.data?.detail ?? e.message));
    }
  };

  const sideColor = side === "BUY" ? "#ef5350" : "#26a69a";

  return (
    <div style={{ padding: "8px 14px", borderTop: "1px solid #21262d", background: "#0e1117" }}>
      <Space size="middle" wrap align="center">
        <Segmented
          size="small"
          value={side}
          onChange={(v) => setSide(v as Side)}
          options={[
            { label: <span style={{ color: "#ef5350", fontWeight: 600 }}>买入 F1</span>, value: "BUY" },
            { label: <span style={{ color: "#26a69a", fontWeight: 600 }}>卖出 F2</span>, value: "SELL" },
          ]}
        />
        <Segmented
          size="small"
          value={orderType}
          onChange={(v) => setOrderType(v as OrderType)}
          options={[
            { label: "限价", value: "LIMIT" },
            { label: "市价", value: "MARKET" },
          ]}
        />
        <span style={{ fontSize: 12, color: "#9ba8b8" }}>
          {currentSymbol ? <SymbolTag code={currentSymbol} showCode={false} /> : "--"}
          {currentQuote ? `  ¥${currentQuote.price.toFixed(2)}` : ""}
        </span>
      </Space>

      <Space size="middle" style={{ marginTop: 8, width: "100%" }} wrap>
        {orderType === "LIMIT" && (
          <span>
            <label style={{ marginRight: 6, fontSize: 12, color: "#9ba8b8" }}>价格</label>
            <InputNumber
              size="small"
              style={{ width: 110 }}
              value={price ?? undefined}
              onChange={(v) => setPrice(v as number | null)}
              step={0.01}
              min={0}
            />
          </span>
        )}
        <span>
          <label style={{ marginRight: 6, fontSize: 12, color: "#9ba8b8" }}>数量</label>
          <InputNumber
            size="small"
            style={{ width: 110 }}
            value={qty ?? undefined}
            onChange={(v) => setQty(v as number | null)}
            step={100}
            min={0}
          />
        </span>
        <Segmented
          size="small"
          value={qty ?? undefined}
          onChange={(v) => setQty(v as number)}
          options={[100, 500, 1000, 5000].map((n) => ({ label: String(n), value: n }))}
        />
        <Button type="primary" style={{ background: sideColor, borderColor: sideColor }} onClick={submit}>
          {side === "BUY" ? "买入" : "卖出"} (Enter)
        </Button>
      </Space>
    </div>
  );
}