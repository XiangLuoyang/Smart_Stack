import { Button, Select, Space, Statistic, Tooltip } from "antd";
import { useEffect } from "react";
import { useStore } from "../stores/useStore";
import { createAccount } from "../api/client";
import SymbolTag from "./SymbolTag";

export default function WorkbenchHeader() {
  const accounts = useStore((s) => s.accounts);
  const currentAccountId = useStore((s) => s.currentAccountId);
  const selectAccount = useStore((s) => s.selectAccount);
  const overview = useStore((s) => s.overview);
  const currentSymbol = useStore((s) => s.currentSymbol);

  const fmt = (n: number, dp = 2) =>
    n.toLocaleString("zh-CN", { minimumFractionDigits: dp, maximumFractionDigits: dp });

  const profit = overview?.floating_profit ?? 0;
  const profitColor = profit > 0 ? "#ef5350" : profit < 0 ? "#26a69a" : "#9ba8b8";

  const handleNewAccount = async () => {
    const name = window.prompt("账户名称", "纸面账户");
    if (!name) return;
    const cashStr = window.prompt("初始资金", "1000000");
    const cash = Number(cashStr);
    if (!cash || cash <= 0) return;
    await createAccount(name, cash);
    await useStore.getState().loadAccounts();
  };

  // auto-refresh overview every 15s
  useEffect(() => {
    const t = setInterval(() => {
      if (useStore.getState().currentAccountId) {
        useStore.getState().refreshOverview();
      }
    }, 15_000);
    return () => clearInterval(t);
  }, []);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 20,
        height: 48,
        padding: "0 16px",
        background: "#0b0e14",
        borderBottom: "1px solid #21262d",
        color: "#e6edf3",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div
          style={{
            width: 22,
            height: 22,
            borderRadius: 4,
            background: "linear-gradient(135deg,#2f7bff,#16c8a8)",
          }}
        />
        <span style={{ fontSize: 15, fontWeight: 600, letterSpacing: 0.5 }}>Smart Stack</span>
      </div>

      <Space size={6}>
        <span style={{ color: "#6e7681", fontSize: 11 }}>账户</span>
        <Select
          size="small"
          style={{ width: 160 }}
          value={currentAccountId ?? undefined}
          onChange={selectAccount}
          options={accounts.map((a) => ({ value: a.id, label: a.name }))}
          placeholder="选择账户"
        />
        <Button size="small" onClick={handleNewAccount}>
          新建
        </Button>
      </Space>

      {currentSymbol && (
        <div style={{ display: "flex", alignItems: "center", padding: "0 8px", borderLeft: "1px solid #21262d", borderRight: "1px solid #21262d" }}>
          <SymbolTag code={currentSymbol} strongName />
        </div>
      )}

      <Space size={28} style={{ marginLeft: "auto" }}>
        <Statistic
          title={<span style={{ color: "#6e7681", fontSize: 11 }}>总资产</span>}
          value={overview ? fmt(overview.total_assets) : "--"}
          valueStyle={{ color: "#e6edf3", fontSize: 15 }}
        />
        <Statistic
          title={<span style={{ color: "#6e7681", fontSize: 11 }}>可用现金</span>}
          value={overview ? fmt(overview.cash) : "--"}
          valueStyle={{ color: "#e6edf3", fontSize: 15 }}
        />
        <Statistic
          title={<span style={{ color: "#6e7681", fontSize: 11 }}>浮动盈亏</span>}
          value={overview ? `${profit >= 0 ? "+" : ""}${fmt(profit)}` : "--"}
          valueStyle={{ color: profitColor, fontSize: 15 }}
        />
      </Space>

      <Tooltip title="F1 买入  F2 卖出  Enter 确认  Esc 撤单">
        <span style={{ color: "#6e7681", fontSize: 11 }}>F1/F2 下单</span>
      </Tooltip>
    </div>
  );
}