import { Alert, Card, Empty, Table, Tag, Tooltip, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { getSignal, refreshSignal } from "../api/client";
import { useStore } from "../stores/useStore";
import type { SignalOut } from "../types";
import ReactMarkdown from "react-markdown";

const { Text } = Typography;

export default function SidePanel() {
  const currentSymbol = useStore((s) => s.currentSymbol);
  const overview = useStore((s) => s.overview);
  const [signal, setSignal] = useState<SignalOut | null>(null);
  const [loadingSig, setLoadingSig] = useState(false);
  const [showReport, setShowReport] = useState(false);

  useEffect(() => {
    if (!currentSymbol) { setSignal(null); return; }
    getSignal(currentSymbol).then(setSignal).catch(() => setSignal(null));
  }, [currentSymbol]);

  const doRefresh = async (source: "LSTM" | "LLM" | "ALL") => {
    if (!currentSymbol) return;
    setLoadingSig(true);
    try {
      await refreshSignal(currentSymbol, source);
      const fresh = await getSignal(currentSymbol);
      setSignal(fresh);
      message.success("信号已刷新");
    } finally {
      setLoadingSig(false);
    }
  };

  return (
    <div style={{ padding: 8, display: "flex", flexDirection: "column", gap: 8, height: "100%", overflow: "auto" }}>
      <Card size="small" title="分析信号" extra={
        <Tooltip title="刷新信号(LSTM + LLM)">
          <Tag color="blue" style={{ cursor: loadingSig ? "wait" : "pointer" }} onClick={() => doRefresh("ALL")}>
            {loadingSig ? "刷新中" : "刷新"}
          </Tag>
        </Tooltip>
      }>
        {signal?.lstm ? (
          <div style={{ marginBottom: 8 }}>
            <Text strong>LSTM 预期收益:</Text>{" "}
            <Text style={{
              color: signal.lstm.score >= 0 ? "#f5222d" : "#52c41a",
              fontSize: 16, fontWeight: 600
            }}>
              {(signal.lstm.score * 100).toFixed(2)}%
            </Text>
          </div>
        ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无 LSTM 信号" />}

        <Alert
          type="warning"
          message="信号仅作参考,不构成投资建议,不自动下单"
          style={{ margin: "8px 0", fontSize: 12 }}
        />

        {signal?.llm ? (
          <div>
            <a onClick={() => setShowReport(!showReport)} style={{ fontSize: 12 }}>
              {showReport ? "收起 LLM 报告 ▲" : "展开 LLM 报告 ▼"}
            </a>
            {showReport && (
              <div style={{ maxHeight: 240, overflow: "auto", fontSize: 12, marginTop: 4 }}>
                <ReactMarkdown>
                  {String((signal.llm as any).report_markdown ?? "")}
                </ReactMarkdown>
              </div>
            )}
          </div>
        ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无 LLM 报告" />}
      </Card>

      <Card size="small" title="持仓" style={{ flex: 1, overflow: "auto" }}>
        <Table
          size="small"
          rowKey="symbol"
          dataSource={overview?.positions ?? []}
          pagination={false}
          scroll={{ y: 240 }}
          locale={{ emptyText: "暂无持仓" }}
          columns={[
            { title: "代码", dataIndex: "symbol", width: 80 },
            { title: "数量", dataIndex: "qty", width: 70, align: "right" as const, render: (v: number) => v.toFixed(0) },
            { title: "成本", dataIndex: "avg_cost", width: 70, align: "right" as const, render: (v: number) => v.toFixed(2) },
            { title: "现价", dataIndex: "last_price", width: 70, align: "right" as const, render: (v: number | null) => v?.toFixed(2) ?? "--" },
            {
              title: "盈亏", width: 90, align: "right" as const,
              render: (_: unknown, r: any) => {
                const p = r.profit as number;
                const pct = (r.profit_pct as number) * 100;
                return (
                  <span style={{ color: p >= 0 ? "#f5222d" : "#52c41a", fontSize: 12 }}>
                    {p >= 0 ? "+" : ""}{p.toFixed(0)} ({pct >= 0 ? "+" : ""}{pct.toFixed(2)}%)
                  </span>
                );
              },
            },
          ]}
        />
      </Card>
    </div>
  );
}
