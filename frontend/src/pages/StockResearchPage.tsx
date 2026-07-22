import { useEffect, useState } from "react";
import { Card, Col, Descriptions, Row, Tag, Typography, Empty, Spin, Input } from "antd";
import { getStockResearch } from "../api/client";
import type { StockResearchView } from "../types";

const { Title, Text, Paragraph } = Typography;

interface Props {
  symbol?: string;
}

function StatusTag({ status }: { status: string }) {
  const color = status === "READY" ? "green" : status === "STALE" ? "orange" : status === "DEGRADED" ? "gold" : "default";
  return <Tag color={color}>{status}</Tag>;
}

export default function StockResearchPage({ symbol: initialSymbol }: Props) {
  const [symbol, setSymbol] = useState(initialSymbol ?? "");
  const [view, setView] = useState<StockResearchView | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (initialSymbol) setSymbol(initialSymbol);
  }, [initialSymbol]);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    getStockResearch(symbol)
      .then(setView)
      .catch(() => setView(null))
      .finally(() => setLoading(false));
  }, [symbol]);

  return (
    <div style={{ padding: 24, overflow: "auto", height: "100%" }}>
      <div style={{ marginBottom: 16, display: "flex", gap: 12, alignItems: "center" }}>
        <Title level={4} style={{ color: "#e6edf3", margin: 0 }}>单股研究</Title>
        <Input.Search
          placeholder="输入股票代码"
          defaultValue={symbol}
          onSearch={(v) => setSymbol(v.trim())}
          style={{ width: 200 }}
          allowClear
        />
      </div>

      {loading && <Spin style={{ display: "block", margin: "40px auto" }} />}

      {!loading && !view && symbol && <Empty description="无数据" />}
      {!loading && !symbol && <Empty description="请输入股票代码" />}

      {!loading && view && (
        <Row gutter={[16, 16]}>
          <Col span={8}>
            <Card size="small" title={<span>行情 <StatusTag status={view.quote.status} /></span>} style={{ background: "#161b22", borderColor: "#21262d" }}>
              {view.quote.price != null ? (
                <Descriptions column={1} size="small" labelStyle={{ color: "#8b949e" }} contentStyle={{ color: "#e6edf3" }}>
                  <Descriptions.Item label="最新价">{view.quote.price.toFixed(2)}</Descriptions.Item>
                  <Descriptions.Item label="涨跌幅">{view.quote.change_pct != null ? `${view.quote.change_pct.toFixed(2)}%` : "-"}</Descriptions.Item>
                  <Descriptions.Item label="数据截止">{view.data_cutoff ?? "-"}</Descriptions.Item>
                </Descriptions>
              ) : <Text style={{ color: "#8b949e" }}>暂无行情</Text>}
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" title={<span>预测 <StatusTag status={view.forecast.status} /></span>} style={{ background: "#161b22", borderColor: "#21262d" }}>
              {view.forecast.status === "READY" ? (
                <Descriptions column={1} size="small" labelStyle={{ color: "#8b949e" }} contentStyle={{ color: "#e6edf3" }}>
                  <Descriptions.Item label="期限">{view.forecast.horizon_days} 交易日</Descriptions.Item>
                  <Descriptions.Item label="上涨概率">{((view.forecast.p_up ?? 0) * 100).toFixed(1)}%</Descriptions.Item>
                  <Descriptions.Item label="中位收益">{((view.forecast.median_return ?? 0) * 100).toFixed(2)}%</Descriptions.Item>
                  <Descriptions.Item label="超额收益">{((view.forecast.expected_excess_return ?? 0) * 100).toFixed(2)}%</Descriptions.Item>
                  <Descriptions.Item label="模型">{view.forecast.model_name} v{view.forecast.model_version}</Descriptions.Item>
                </Descriptions>
              ) : <Text style={{ color: "#8b949e" }}>暂无预测</Text>}
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" title={<span>技术 <StatusTag status={view.technical.status} /></span>} style={{ background: "#161b22", borderColor: "#21262d" }}>
              {view.technical.status === "READY" ? (
                <Descriptions column={1} size="small" labelStyle={{ color: "#8b949e" }} contentStyle={{ color: "#e6edf3" }}>
                  <Descriptions.Item label="RSI">{view.technical.rsi?.toFixed(1) ?? "-"}</Descriptions.Item>
                  <Descriptions.Item label="MACD">{view.technical.macd?.toFixed(3) ?? "-"}</Descriptions.Item>
                  <Descriptions.Item label="MA5">{view.technical.ma5?.toFixed(2) ?? "-"}</Descriptions.Item>
                  <Descriptions.Item label="MA20">{view.technical.ma20?.toFixed(2) ?? "-"}</Descriptions.Item>
                </Descriptions>
              ) : <Text style={{ color: "#8b949e" }}>暂无技术指标</Text>}
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" title={<span>风险 <StatusTag status={view.risk.status} /></span>} style={{ background: "#161b22", borderColor: "#21262d" }}>
              {view.risk.status === "READY" ? (
                <Descriptions column={1} size="small" labelStyle={{ color: "#8b949e" }} contentStyle={{ color: "#e6edf3" }}>
                  <Descriptions.Item label="年化波动率">{view.risk.annualized_volatility?.toFixed(2)}%</Descriptions.Item>
                  <Descriptions.Item label="最大回撤">{view.risk.max_drawdown?.toFixed(2)}%</Descriptions.Item>
                  <Descriptions.Item label="夏普比率">{view.risk.sharpe_ratio?.toFixed(3)}</Descriptions.Item>
                </Descriptions>
              ) : <Text style={{ color: "#8b949e" }}>暂无风险数据</Text>}
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" title={<span>LLM <StatusTag status={view.llm.status} /></span>} style={{ background: "#161b22", borderColor: "#21262d" }}>
              {view.llm.report_markdown ? (
                <Paragraph style={{ color: "#e6edf3", whiteSpace: "pre-wrap", maxHeight: 200, overflow: "auto" }}>
                  {view.llm.report_markdown}
                </Paragraph>
              ) : <Text style={{ color: "#8b949e" }}>LLM 报告不可用</Text>}
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" title="研究案例" style={{ background: "#161b22", borderColor: "#21262d" }}>
              {view.active_cases.length > 0 ? (
                view.active_cases.map((c) => (
                  <div key={c.id} style={{ marginBottom: 4 }}>
                    <Tag color="green">ACTIVE</Tag>
                    <Text style={{ color: "#e6edf3" }}>{c.thesis}</Text>
                  </div>
                ))
              ) : <Text style={{ color: "#8b949e" }}>暂无案例</Text>}
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
}