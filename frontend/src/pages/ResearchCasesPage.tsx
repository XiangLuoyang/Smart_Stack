import { useEffect, useState, useCallback } from "react";
import { Card, Col, List, Row, Tag, Typography, Empty, Spin, Button, Popconfirm, message } from "antd";
import { listResearchCases, getResearchCase, closeResearchCase } from "../api/client";
import CaseTimeline from "../components/research/CaseTimeline";
import EvidenceForm from "../components/research/EvidenceForm";
import DecisionForm from "../components/research/DecisionForm";
import type { CaseSummary, ResearchCaseDetail } from "../types";

const { Title, Text } = Typography;

const DIRECTION_COLOR: Record<string, string> = { BULLISH: "green", BEARISH: "red", NEUTRAL: "default" };

export default function ResearchCasesPage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selected, setSelected] = useState<ResearchCaseDetail | null>(null);
  const [loading, setLoading] = useState(false);

  const loadCases = useCallback(() => {
    listResearchCases().then(setCases).catch(() => {});
  }, []);

  useEffect(() => { loadCases(); }, [loadCases]);

  const loadDetail = useCallback((id: string) => {
    setLoading(true);
    getResearchCase(id)
      .then(setSelected)
      .catch(() => setSelected(null))
      .finally(() => setLoading(false));
  }, []);

  const handleClose = async (id: string) => {
    try {
      await closeResearchCase(id);
      message.success("案例已关闭");
      loadCases();
      if (selected?.id === id) loadDetail(id);
    } catch {
      message.error("关闭失败");
    }
  };

  return (
    <div style={{ padding: 24, height: "100%", display: "flex", gap: 16, overflow: "hidden" }}>
      <div style={{ width: 320, overflow: "auto", flexShrink: 0 }}>
        <Title level={5} style={{ color: "#e6edf3" }}>研究案例</Title>
        <List
          dataSource={cases}
          renderItem={(c) => (
            <List.Item
              onClick={() => loadDetail(c.id)}
              style={{ cursor: "pointer", padding: "8px 12px", borderBottom: "1px solid #21262d", background: selected?.id === c.id ? "#1c2128" : "transparent" }}
            >
              <div>
                <Tag color={c.status === "ACTIVE" ? "green" : "default"}>{c.status}</Tag>
                <Tag color={DIRECTION_COLOR[c.initial_direction]}>{c.initial_direction}</Tag>
                <Text style={{ color: "#e6edf3" }}>{c.symbol}</Text>
                <br />
                <Text style={{ color: "#8b949e", fontSize: 12 }}>{c.thesis}</Text>
              </div>
            </List.Item>
          )}
        />
      </div>

      <div style={{ flex: 1, overflow: "auto" }}>
        {loading && <Spin style={{ display: "block", margin: "40px auto" }} />}
        {!loading && !selected && <Empty description="选择一个案例查看详情" />}
        {!loading && selected && (
          <>
            <Row gutter={[16, 16]}>
              <Col span={24}>
                <Card size="small" style={{ background: "#161b22", borderColor: "#21262d" }}
                  title={
                    <span>
                      <Tag color={DIRECTION_COLOR[selected.initial_direction]}>{selected.initial_direction}</Tag>
                      <Text style={{ color: "#e6edf3" }}>{selected.symbol} - {selected.thesis}</Text>
                    </span>
                  }
                  extra={selected.status === "ACTIVE" ? (
                    <Popconfirm title="确认关闭此案例?" onConfirm={() => handleClose(selected.id)}>
                      <Button size="small" danger>关闭案例</Button>
                    </Popconfirm>
                  ) : <Tag>CLOSED</Tag>}
                >
                  <Text style={{ color: "#8b949e" }}>
                    预期收益: {(selected.expected_return_lower * 100).toFixed(1)}% ~ {(selected.expected_return_upper * 100).toFixed(1)}%
                    {" | "}入场: {selected.planned_entry} | 目标: {selected.target_price} | 止损: {selected.stop_price}
                    {" | "}信心: {selected.confidence}/5
                  </Text>
                  <br />
                  <Text style={{ color: "#8b949e" }}>反驳: {selected.counterargument}</Text>
                  <br />
                  <Text style={{ color: "#8b949e" }}>失效条件: {selected.invalidation_condition}</Text>
                </Card>
              </Col>
            </Row>

            {selected.status === "ACTIVE" && (
              <Card size="small" title="追加事件" style={{ background: "#161b22", borderColor: "#21262d", marginTop: 12 }}>
                <EvidenceForm caseId={selected.id} onAppended={() => loadDetail(selected.id)} />
                <DecisionForm caseId={selected.id} onAppended={() => loadDetail(selected.id)} />
              </Card>
            )}

            <Card size="small" title="事件时间线" style={{ background: "#161b22", borderColor: "#21262d", marginTop: 12 }}>
              <CaseTimeline
                evidence={selected.evidence_entries}
                decisions={selected.decision_entries}
                reviews={selected.review_notes}
              />
            </Card>
          </>
        )}
      </div>
    </div>
  );
}