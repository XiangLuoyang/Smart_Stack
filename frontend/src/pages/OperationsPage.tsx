import { Typography } from "antd";

const { Title, Text } = Typography;

export default function OperationsPage() {
  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ color: "#e6edf3" }}>模拟操作</Title>
      <Text style={{ color: "#8b949e" }}>
        两步确认下单:预览 → 确认。所有操作关联研究案例,T+1 可卖。
      </Text>
    </div>
  );
}