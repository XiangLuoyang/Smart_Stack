import { useEffect, useState } from "react";
import { Card, Table, Typography } from "antd";
import http from "../api/client";

const { Title } = Typography;

export default function PerformancePage() {
  const [metrics, setMetrics] = useState<any[]>([]);

  useEffect(() => {
    http.get("/performance/metrics").then((r) => setMetrics(r.data)).catch(() => {});
  }, []);

  const columns = [
    { title: "Scope", dataIndex: "scope", key: "scope" },
    { title: "Metric", dataIndex: "metric_name", key: "metric_name" },
    { title: "Value", dataIndex: "value", key: "value", render: (v: number | null) => v != null ? (v * 100).toFixed(2) + "%" : "-" },
    { title: "Samples", dataIndex: "sample_count", key: "sample_count" },
    { title: "Period", dataIndex: "period_end", key: "period_end" },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ color: "#e6edf3" }}>模型表现</Title>
      <Card size="small" style={{ background: "#161b22", borderColor: "#21262d" }}>
        <Table dataSource={metrics} columns={columns} rowKey="id" size="small" pagination={false} />
      </Card>
    </div>
  );
}