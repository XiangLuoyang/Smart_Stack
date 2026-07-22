import { useState } from "react";
import { Form, Input, InputNumber, Select, Button, message } from "antd";
import { appendDecision } from "../../api/client";

interface Props {
  caseId: string;
  onAppended: () => void;
}

export default function DecisionForm({ caseId, onAppended }: Props) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      await appendDecision(caseId, {
        direction: values.direction,
        action: values.action,
        rationale: values.rationale,
        confidence: values.confidence,
      });
      message.success("决策已追加");
      form.resetFields();
      onAppended();
    } catch (e: any) {
      if (e?.response?.data?.detail) message.error(e.response.data.detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form form={form} layout="inline" style={{ marginBottom: 12, flexWrap: "wrap", gap: 8 }} initialValues={{ direction: "BULLISH", action: "WATCH", confidence: 3 }}>
      <Form.Item name="direction" rules={[{ required: true }]} style={{ marginBottom: 0 }}>
        <Select style={{ width: 90 }} options={[
          { value: "BULLISH", label: "看多" },
          { value: "NEUTRAL", label: "中性" },
          { value: "BEARISH", label: "看空" },
        ]} />
      </Form.Item>
      <Form.Item name="action" rules={[{ required: true }]} style={{ marginBottom: 0 }}>
        <Select style={{ width: 110 }} options={[
          { value: "WATCH", label: "观察" },
          { value: "PLAN_BUY", label: "计划买入" },
          { value: "HOLD", label: "持有" },
          { value: "PLAN_SELL", label: "计划卖出" },
          { value: "EXIT", label: "退出" },
          { value: "NO_ACTION", label: "不操作" },
        ]} />
      </Form.Item>
      <Form.Item name="rationale" rules={[{ required: true }]} style={{ marginBottom: 0, flex: 1 }}>
        <Input placeholder="理由" />
      </Form.Item>
      <Form.Item name="confidence" rules={[{ required: true }]} style={{ marginBottom: 0 }}>
        <InputNumber min={1} max={5} style={{ width: 70 }} />
      </Form.Item>
      <Button type="primary" size="small" onClick={handleSubmit} loading={loading}>追加决策</Button>
    </Form>
  );
}