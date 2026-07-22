import { useState } from "react";
import { Button, Card, Descriptions, Form, Input, InputNumber, Select, Typography, message, Tag, Divider } from "antd";
import http from "../api/client";

const { Title, Text } = Typography;

interface PreviewResult {
  id: string;
  confirmation_token: string;
  expires_at: string;
  fee_estimate: number;
  symbol: string;
  side: string;
  qty: number;
}

export default function OperationsPage() {
  const [form] = Form.useForm();
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [lastResult, setLastResult] = useState<any>(null);

  const handlePreview = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      const resp = await http.post("/orders/preview", {
        account_id: values.account_id,
        symbol: values.symbol,
        side: values.side,
        qty: values.qty,
        order_type: values.order_type,
        price: values.price || null,
        research_case_id: values.research_case_id || null,
      });
      setPreview(resp.data);
      message.info("预览已生成,请确认后下单");
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "预览失败");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!preview) return;
    try {
      setConfirming(true);
      const resp = await http.post("/orders/confirm", {
        preview_id: preview.id,
        confirmation_token: preview.confirmation_token,
        idempotency_key: `ui-${Date.now()}`,
      });
      setLastResult(resp.data);
      setPreview(null);
      message.success(`订单已${resp.data.status === "FILLED" ? "成交" : "提交"}`);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "确认失败");
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 700 }}>
      <Title level={4} style={{ color: "#e6edf3" }}>模拟操作</Title>
      <Text style={{ color: "#8b949e" }}>两步确认:预览 → 确认。所有操作关联研究案例,T+1 可卖。</Text>

      <Card size="small" style={{ background: "#161b22", borderColor: "#21262d", marginTop: 16 }}>
        <Form form={form} layout="vertical" initialValues={{ side: "BUY", order_type: "LIMIT", qty: 100 }}>
          <Form.Item name="account_id" label="账户 ID" rules={[{ required: true }]}>
            <Input placeholder="账户 ID" />
          </Form.Item>
          <Form.Item name="symbol" label="股票代码" rules={[{ required: true }]}>
            <Input placeholder="000001" />
          </Form.Item>
          <Form.Item name="side" label="方向" rules={[{ required: true }]}>
            <Select options={[{ value: "BUY", label: "买入" }, { value: "SELL", label: "卖出" }]} />
          </Form.Item>
          <Form.Item name="qty" label="数量(股)" rules={[{ required: true }]}>
            <InputNumber min={100} step={100} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="order_type" label="类型">
            <Select options={[{ value: "LIMIT", label: "限价" }, { value: "MARKET", label: "市价" }]} />
          </Form.Item>
          <Form.Item name="price" label="限价(限价单必填)">
            <InputNumber step={0.01} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="research_case_id" label="关联研究案例 ID">
            <Input placeholder="可选" />
          </Form.Item>
          <Button type="primary" onClick={handlePreview} loading={loading} block>
            生成预览
          </Button>
        </Form>
      </Card>

      {preview && (
        <Card size="small" title="订单预览" style={{ background: "#161b22", borderColor: "#21262d", marginTop: 12 }}
          extra={<Tag color="orange">待确认</Tag>}>
          <Descriptions column={2} size="small" labelStyle={{ color: "#8b949e" }} contentStyle={{ color: "#e6edf3" }}>
            <Descriptions.Item label="代码">{preview.symbol}</Descriptions.Item>
            <Descriptions.Item label="方向">{preview.side === "BUY" ? "买入" : "卖出"}</Descriptions.Item>
            <Descriptions.Item label="数量">{preview.qty}</Descriptions.Item>
            <Descriptions.Item label="预估费用">{preview.fee_estimate?.toFixed(2)}</Descriptions.Item>
            <Descriptions.Item label="有效期至">{preview.expires_at?.slice(0, 19)}</Descriptions.Item>
          </Descriptions>
          <Divider style={{ margin: "12px 0" }} />
          <Button type="primary" danger onClick={handleConfirm} loading={confirming} block>
            确认下单
          </Button>
        </Card>
      )}

      {lastResult && (
        <Card size="small" title="执行结果" style={{ background: "#161b22", borderColor: "#21262d", marginTop: 12 }}>
          <Descriptions column={1} size="small" labelStyle={{ color: "#8b949e" }} contentStyle={{ color: "#e6edf3" }}>
            <Descriptions.Item label="订单 ID">{lastResult.order_id}</Descriptions.Item>
            <Descriptions.Item label="状态"><Tag color={lastResult.status === "FILLED" ? "green" : "orange"}>{lastResult.status}</Tag></Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </div>
  );
}