import { useEffect, useState } from "react";
import { Card, Col, Row, Tag, Typography, Empty } from "antd";
import { listScreenerRuns, listResearchCases } from "../api/client";
import type { ScreeningRun, CaseSummary } from "../types";

const { Title, Text } = Typography;

export default function TodayPage() {
  const [latestRun, setLatestRun] = useState<ScreeningRun | null>(null);
  const [activeCases, setActiveCases] = useState<CaseSummary[]>([]);

  useEffect(() => {
    listScreenerRuns({ limit: 1 })
      .then((runs) => setLatestRun(runs[0] ?? null))
      .catch(() => {});
    listResearchCases({ status: "ACTIVE" })
      .then(setActiveCases)
      .catch(() => {});
  }, []);

  return (
    <div style={{ padding: 24, overflow: "auto", height: "100%" }}>
      <Title level={4} style={{ color: "#e6edf3" }}>今日概览</Title>
      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card size="small" title="最新筛选" style={{ background: "#161b22", borderColor: "#21262d" }}>
            {latestRun ? (
              <>
                <Text style={{ color: "#8b949e" }}>
                  {latestRun.business_date} | 状态: <Tag color={latestRun.status === "SUCCESS" ? "green" : "orange"}>{latestRun.status}</Tag>
                </Text>
                <br />
                <Text style={{ color: "#8b949e" }}>
                  成功 {latestRun.success_count} / 失败 {latestRun.failure_count}
                </Text>
                {latestRun.top10 && latestRun.top10.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <Text strong style={{ color: "#e6edf3" }}>Top 10</Text>
                    <div style={{ marginTop: 4 }}>
                      {latestRun.top10.map((c) => (
                        <Tag key={c.id} style={{ marginBottom: 4 }}>{c.symbol} (#{c.rank})</Tag>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <Empty description="暂无筛选记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" title="活跃研究案例" style={{ background: "#161b22", borderColor: "#21262d" }}>
            {activeCases.length > 0 ? (
              activeCases.map((c) => (
                <div key={c.id} style={{ marginBottom: 8 }}>
                  <Tag color={c.initial_direction === "BULLISH" ? "green" : c.initial_direction === "BEARISH" ? "red" : "default"}>
                    {c.initial_direction}
                  </Tag>
                  <Text style={{ color: "#e6edf3" }}>{c.symbol}</Text>
                  <Text style={{ color: "#8b949e", marginLeft: 8 }}>{c.thesis}</Text>
                </div>
              ))
            ) : (
              <Empty description="暂无活跃案例" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" title="到期复盘" style={{ background: "#161b22", borderColor: "#21262d" }}>
            <Text style={{ color: "#8b949e" }}>尚未启用</Text>
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" title="模拟操作" style={{ background: "#161b22", borderColor: "#21262d" }}>
            <Text style={{ color: "#8b949e" }}>尚未启用</Text>
          </Card>
        </Col>
      </Row>
    </div>
  );
}