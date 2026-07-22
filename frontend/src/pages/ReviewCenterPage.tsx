import { useEffect, useState, useCallback } from "react";
import { Card, Col, Descriptions, List, Row, Tabs, Tag, Typography, Empty, Spin } from "antd";
import http from "../api/client";
import ReviewForm from "../components/research/ReviewForm";

const { Title, Text } = Typography;

interface ReviewDetail {
  prediction_id: string;
  symbol: string;
  business_date: string;
  horizon_days: number;
  state: string;
  median_return: number;
  expected_excess_return: number;
  review: {
    actual_return: number | null;
    benchmark_excess: number | null;
    signed_error: number | null;
    interval_coverage: boolean | null;
    mfe: number | null;
    mae: number | null;
    direction_correct: boolean | null;
    state: string;
  } | null;
  cases: Array<{ id: string; thesis: string; status: string }>;
  notes: Array<{ id: string; content: string; created_at: string }>;
}

export default function ReviewCenterPage() {
  const [dueList, setDueList] = useState<any[]>([]);
  const [settledList, setSettedList] = useState<any[]>([]);
  const [detail, setDetail] = useState<ReviewDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    http.get("/reviews", { params: { state: "DUE" } }).then((r) => setDueList(r.data)).catch(() => {});
    http.get("/reviews", { params: { state: "SETTLED" } }).then((r) => setSettedList(r.data)).catch(() => {});
  }, []);

  const loadDetail = useCallback((id: string) => {
    setLoading(true);
    http.get(`/reviews/${id}`).then((r) => setDetail(r.data)).catch(() => setDetail(null)).finally(() => setLoading(false));
  }, []);

  const renderList = (items: any[]) => (
    <List
      dataSource={items}
      renderItem={(item: any) => (
        <List.Item onClick={() => loadDetail(item.id)} style={{ cursor: "pointer", padding: "8px 12px", borderBottom: "1px solid #21262d" }}>
          <Text style={{ color: "#e6edf3" }}>{item.symbol}</Text>
          <Text style={{ color: "#8b949e", marginLeft: 12 }}>{item.business_date}</Text>
          <Tag style={{ marginLeft: 8 }} color={item.state === "SETTLED" ? "green" : "orange"}>{item.state}</Tag>
        </List.Item>
      )}
    />
  );

  return (
    <div style={{ padding: 24, height: "100%", display: "flex", gap: 16, overflow: "hidden" }}>
      <div style={{ width: 360, overflow: "auto", flexShrink: 0 }}>
        <Title level={5} style={{ color: "#e6edf3" }}>复盘中心</Title>
        <Tabs
          size="small"
          items={[
            { key: "due", label: `待复盘 (${dueList.length})`, children: renderList(dueList) },
            { key: "done", label: `已完成 (${settledList.length})`, children: renderList(settledList) },
          ]}
        />
      </div>

      <div style={{ flex: 1, overflow: "auto" }}>
        {loading && <Spin style={{ display: "block", margin: "40px auto" }} />}
        {!loading && !detail && <Empty description="选择一条预测查看复盘详情" />}
        {!loading && detail && (
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <Card size="small" title={`${detail.symbol} - ${detail.business_date}`} style={{ background: "#161b22", borderColor: "#21262d" }}>
                <Descriptions column={3} size="small" labelStyle={{ color: "#8b949e" }} contentStyle={{ color: "#e6edf3" }}>
                  <Descriptions.Item label="预测中位收益">{(detail.median_return * 100).toFixed(2)}%</Descriptions.Item>
                  <Descriptions.Item label="实际收益">{detail.review?.actual_return != null ? `${(detail.review.actual_return * 100).toFixed(2)}%` : "-"}</Descriptions.Item>
                  <Descriptions.Item label="方向正确">{detail.review?.direction_correct != null ? (detail.review.direction_correct ? "是" : "否") : "-"}</Descriptions.Item>
                  <Descriptions.Item label="区间覆盖">{detail.review?.interval_coverage != null ? (detail.review.interval_coverage ? "是" : "否") : "-"}</Descriptions.Item>
                  <Descriptions.Item label="MFE">{detail.review?.mfe != null ? `${(detail.review.mfe * 100).toFixed(2)}%` : "-"}</Descriptions.Item>
                  <Descriptions.Item label="MAE">{detail.review?.mae != null ? `${(detail.review.mae * 100).toFixed(2)}%` : "-"}</Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
            {detail.cases.length > 0 && (
              <Col span={24}>
                <Card size="small" title="关联案例" style={{ background: "#161b22", borderColor: "#21262d" }}>
                  {detail.cases.map((c) => (
                    <div key={c.id}><Tag color={c.status === "ACTIVE" ? "green" : "default"}>{c.status}</Tag> <Text style={{ color: "#e6edf3" }}>{c.thesis}</Text></div>
                  ))}
                </Card>
              </Col>
            )}
            <Col span={12}>
              <Card size="small" title="提交复盘" style={{ background: "#161b22", borderColor: "#21262d" }}>
                <ReviewForm predictionId={detail.prediction_id} onSubmitted={() => loadDetail(detail.prediction_id)} />
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" title="已有笔记" style={{ background: "#161b22", borderColor: "#21262d" }}>
                {detail.notes.length > 0 ? detail.notes.map((n) => (
                  <div key={n.id} style={{ marginBottom: 8 }}>
                    <Text style={{ color: "#e6edf3" }}>{n.content}</Text>
                    <br /><Text style={{ color: "#6e7681", fontSize: 11 }}>{n.created_at?.slice(0, 19)}</Text>
                  </div>
                )) : <Text style={{ color: "#8b949e" }}>暂无笔记</Text>}
              </Card>
            </Col>
          </Row>
        )}
      </div>
    </div>
  );
}