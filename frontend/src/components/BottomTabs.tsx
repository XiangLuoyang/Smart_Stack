import { Button, DatePicker, Form, InputNumber, Modal, Select, Space, Table, Tabs, Tag, message } from "antd";
import dayjs from "dayjs";
import { useState } from "react";
import { useStore } from "../stores/useStore";
import { cancelOrder, listBacktestRuns, runBacktest, updateRiskRule } from "../api/client";
import type { BacktestRun } from "../types";

const { RangePicker } = DatePicker;

export default function BottomTabs() {
  const orders = useStore((s) => s.orders);
  const trades = useStore((s) => s.trades);
  const currentSymbol = useStore((s) => s.currentSymbol);
  const loadOrders = useStore((s) => s.loadOrders);
  const [backtestModal, setBacktestModal] = useState(false);
  const [backtestRuns, setBacktestRuns] = useState<BacktestRun[]>([]);

  const statusColor: Record<string, string> = {
    PENDING: "processing",
    FILLED: "green",
    CANCELLED: "default",
    REJECTED: "red",
  };

  const pendingOrders = orders.filter((o) => o.status === "PENDING");
  const filledOrders = orders.filter((o) => ["FILLED", "REJECTED", "CANCELLED"].includes(o.status));

  const handleCancel = async (id: string) => {
    try {
      await cancelOrder(id);
      message.success("已撤单");
      await loadOrders();
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? "撤单失败");
    }
  };

  const loadBacktestRuns = async () => {
    setBacktestRuns(await listBacktestRuns());
  };

  return (
    <div style={{ height: 240, borderTop: "1px solid #e8e8e8", background: "#fff" }}>
      <Tabs
        defaultActiveKey="pending"
        size="small"
        style={{ padding: "0 12px", height: "100%" }}
        items={[
          {
            key: "pending",
            label: `委托中 (${pendingOrders.length})`,
            children: (
              <Table
                size="small"
                rowKey="id"
                dataSource={pendingOrders}
                pagination={false}
                scroll={{ y: 140 }}
                locale={{ emptyText: "无挂单" }}
                columns={[
                  { title: "时间", dataIndex: "created_at", width: 160, render: (v: string) => dayjs(v).format("MM-DD HH:mm:ss") },
                  { title: "代码", dataIndex: "symbol", width: 90 },
                  { title: "方向", dataIndex: "side", width: 70, render: (v: string) => <Tag color={v === "BUY" ? "red" : "green"}>{v === "BUY" ? "买" : "卖"}</Tag> },
                  { title: "类型", dataIndex: "order_type", width: 70 },
                  { title: "价格", dataIndex: "price", width: 80, align: "right" as const, render: (v: number | null) => v?.toFixed(2) ?? "--" },
                  { title: "数量", dataIndex: "qty", width: 80, align: "right" as const },
                  { title: "状态", dataIndex: "status", width: 80, render: (v: string) => <Tag color={statusColor[v]}>{v}</Tag> },
                  {
                    title: "操作", width: 80,
                    render: (_: unknown, r: any) => (
                      <Button size="small" danger onClick={() => handleCancel(r.id)}>撤单</Button>
                    ),
                  },
                ]}
              />
            ),
          },
          {
            key: "filled",
            label: `成交/历史 (${trades.length})`,
            children: (
              <Table
                size="small"
                rowKey="id"
                dataSource={trades}
                pagination={false}
                scroll={{ y: 140 }}
                locale={{ emptyText: "无成交记录" }}
                columns={[
                  { title: "时间", dataIndex: "filled_at", width: 160, render: (v: string) => dayjs(v).format("MM-DD HH:mm:ss") },
                  { title: "代码", dataIndex: "symbol", width: 90 },
                  { title: "方向", dataIndex: "side", width: 70, render: (v: string) => <Tag color={v === "BUY" ? "red" : "green"}>{v === "BUY" ? "买" : "卖"}</Tag> },
                  { title: "数量", dataIndex: "qty", width: 80, align: "right" as const },
                  { title: "价格", dataIndex: "price", width: 80, align: "right" as const, render: (v: number) => v.toFixed(2) },
                  { title: "佣金", dataIndex: "commission", width: 80, align: "right" as const, render: (v: number) => v.toFixed(2) },
                  { title: "印花税", dataIndex: "stamp_duty", width: 80, align: "right" as const, render: (v: number) => v.toFixed(2) },
                  { title: "过户费", dataIndex: "transfer_fee", width: 80, align: "right" as const, render: (v: number) => v.toFixed(2) },
                ]}
              />
            ),
          },
          {
            key: "risk",
            label: "风控规则",
            children: <RiskRuleEditor />,
          },
          {
            key: "backtest",
            label: "回测",
            children: (
              <div style={{ padding: 8 }}>
                <Space>
                  <Button size="small" type="primary" onClick={() => setBacktestModal(true)}>新建回测</Button>
                  <Button size="small" onClick={loadBacktestRuns}>刷新列表</Button>
                </Space>
                <Table
                  size="small"
                  rowKey="id"
                  style={{ marginTop: 8 }}
                  dataSource={backtestRuns}
                  pagination={false}
                  scroll={{ y: 120 }}
                  locale={{ emptyText: "点击刷新列表" }}
                  columns={[
                    { title: "策略", dataIndex: "strategy_name", width: 100 },
                    { title: "区间", width: 200, render: (_: unknown, r: BacktestRun) => `${dayjs(r.start).format("YYYY-MM-DD")} ~ ${dayjs(r.end).format("YYYY-MM-DD")}` },
                    { title: "指标", render: (_: unknown, r: BacktestRun) => {
                      try {
                        const m = JSON.parse(r.metrics_json);
                        return (
                          <span style={{ fontSize: 12 }}>
                            收益率 <b style={{ color: m.total_return >= 0 ? "#f5222d" : "#52c41a" }}>{(m.total_return * 100).toFixed(2)}%</b>
                            {" "}夏普 {m.sharpe?.toFixed(2)}
                            {" "}回撤 {(m.max_drawdown * 100).toFixed(1)}%
                            {" "}胜率 {(m.win_rate * 100).toFixed(0)}%
                            {" "}交易 {m.trade_count} 笔
                          </span>
                        );
                      } catch { return "--"; }
                    }},
                  ]}
                />
              </div>
            ),
          },
        ]}
      />

      <BacktestModal open={backtestModal} onClose={() => setBacktestModal(false)} defaultSymbol={currentSymbol ?? ""} />
    </div>
  );
}

function RiskRuleEditor() {
  const riskRule = useStore((s) => s.riskRule);
  const loadRiskRule = useStore((s) => s.loadRiskRule);
  const [form] = Form.useForm();

  if (!riskRule) return <div style={{ padding: 16 }}>请先选择账户</div>;

  const handleSave = async () => {
    const v = await form.validateFields();
    await updateRiskRule(riskRule.account_id, {
      max_position_pct: v.max_position_pct,
      max_single_pct: v.max_single_pct,
      stop_loss_pct: v.stop_loss_pct,
      take_profit_pct: v.take_profit_pct,
      max_daily_trades: v.max_daily_trades,
    });
    message.success("风控规则已更新");
    await loadRiskRule();
  };

  return (
    <Form form={form} layout="inline" size="small" initialValues={riskRule} style={{ padding: 8, gap: 8 }}>
      <Form.Item label="总仓位上限" name="max_position_pct"><InputNumber min={0} max={1} step={0.1} style={{ width: 80 }} /></Form.Item>
      <Form.Item label="单票上限" name="max_single_pct"><InputNumber min={0} max={1} step={0.05} style={{ width: 80 }} /></Form.Item>
      <Form.Item label="止损" name="stop_loss_pct"><InputNumber min={0} max={1} step={0.01} style={{ width: 80 }} /></Form.Item>
      <Form.Item label="止盈" name="take_profit_pct"><InputNumber min={0} max={1} step={0.01} style={{ width: 80 }} /></Form.Item>
      <Form.Item label="日内笔数" name="max_daily_trades"><InputNumber min={1} max={1000} style={{ width: 80 }} /></Form.Item>
      <Form.Item><Button type="primary" onClick={handleSave}>保存</Button></Form.Item>
    </Form>
  );
}

function BacktestModal({ open, onClose, defaultSymbol }: { open: boolean; onClose: () => void; defaultSymbol: string }) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleRun = async () => {
    const v = await form.validateFields();
    setLoading(true);
    try {
      const range = v.range as [dayjs.Dayjs, dayjs.Dayjs];
      await runBacktest({
        symbol: v.symbol,
        strategy_name: v.strategy_name,
        params: { fast: v.fast ?? 5, slow: v.slow ?? 20 },
        start: range[0].format("YYYY-MM-DDTHH:mm:ss"),
        end: range[1].format("YYYY-MM-DDTHH:mm:ss"),
        initial_cash: v.initial_cash ?? 1_000_000,
      });
      message.success("回测完成");
      onClose();
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? "回测失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} title="新建回测" onCancel={onClose} onOk={handleRun} confirmLoading={loading} okText="开始回测" width={480}>
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          symbol: defaultSymbol,
          strategy_name: "ma_cross",
          fast: 5,
          slow: 20,
          initial_cash: 1_000_000,
          range: [dayjs().subtract(1, "year"), dayjs()],
        }}
      >
        <Form.Item label="标的" name="symbol" rules={[{ required: true }]}>
          <InputNumber style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item label="策略" name="strategy_name" rules={[{ required: true }]}>
          <Select options={[{ value: "ma_cross", label: "双均线(fast 上穿 slow 买入)" }]} />
        </Form.Item>
        <Form.Item label="均线参数">
          <Space>
            <Form.Item name="fast" noStyle><InputNumber addonBefore="fast" /></Form.Item>
            <Form.Item name="slow" noStyle><InputNumber addonBefore="slow" /></Form.Item>
          </Space>
        </Form.Item>
        <Form.Item label="回测区间" name="range" rules={[{ required: true }]}>
          <RangePicker />
        </Form.Item>
        <Form.Item label="初始资金" name="initial_cash">
          <InputNumber style={{ width: "100%" }} min={1000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
