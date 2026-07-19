import { Button, Select, Space, Statistic, Tag, Tooltip } from "antd";
import { useEffect } from "react";
import { useStore } from "../stores/useStore";
import { createAccount } from "../api/client";

export default function WorkbenchHeader() {
  const accounts = useStore((s) => s.accounts);
  const currentAccountId = useStore((s) => s.currentAccountId);
  const selectAccount = useStore((s) => s.selectAccount);
  const overview = useStore((s) => s.overview);

  const fmt = (n: number, dp = 2) =>
    n.toLocaleString("zh-CN", { minimumFractionDigits: dp, maximumFractionDigits: dp });

  const profit = overview?.floating_profit ?? 0;
  const profitColor = profit > 0 ? "#f5222d" : profit < 0 ? "#52c41a" : "#999"; // A 股:红涨绿跌

  const handleNewAccount = async () => {
    const name = window.prompt("账户名称", "纸面账户");
    if (!name) return;
    const cashStr = window.prompt("初始资金", "1000000");
    const cash = Number(cashStr);
    if (!cash || cash <= 0) return;
    await createAccount(name, cash);
    await useStore.getState().loadAccounts();
  };

  // 自动刷新概览(每 15 秒,保持浮动盈亏新鲜)
  useEffect(() => {
    const t = setInterval(() => {
      if (useStore.getState().currentAccountId) {
        useStore.getState().refreshOverview();
      }
    }, 15_000);
    return () => clearInterval(t);
  }, []);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 24, color: "#fff", height: 48 }}>
      <div style={{ fontSize: 16, fontWeight: 600 }}>Smart Stack 操盘工作台</div>

      <Space>
        <span style={{ color: "#bbb" }}>账户:</span>
        <Select
          size="small"
          style={{ width: 180 }}
          value={currentAccountId ?? undefined}
          onChange={selectAccount}
          options={accounts.map((a) => ({ value: a.id, label: a.name }))}
          placeholder="选择账户"
        />
        <Button size="small" onClick={handleNewAccount}>新建</Button>
      </Space>

      <Space size="large">
        <Statistic
          title={<span style={{ color: "#bbb", fontSize: 12 }}>总资产</span>}
          value={overview ? fmt(overview.total_assets) : "--"}
          valueStyle={{ color: "#fff", fontSize: 16 }}
        />
        <Statistic
          title={<span style={{ color: "#bbb", fontSize: 12 }}>可用现金</span>}
          value={overview ? fmt(overview.cash) : "--"}
          valueStyle={{ color: "#fff", fontSize: 16 }}
        />
        <Statistic
          title={<span style={{ color: "#bbb", fontSize: 12 }}>浮动盈亏</span>}
          value={overview ? `${profit >= 0 ? "+" : ""}${fmt(profit)}` : "--"}
          valueStyle={{ color: profitColor, fontSize: 16 }}
        />
      </Space>

      <div style={{ marginLeft: "auto" }}>
        <Tooltip title="F1 买入  F2 卖出  Enter 确认  Esc 撤单">
          <Tag color="blue">键盘下单</Tag>
        </Tooltip>
      </div>
    </div>
  );
}
