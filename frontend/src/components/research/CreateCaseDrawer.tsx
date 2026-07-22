import { useState } from "react";
import { Drawer, Form, Input, InputNumber, Select, Button, message } from "antd";
import { createResearchCase } from "../../api/client";
import type { CaseCreate } from "../../types";

interface Props {
  open: boolean;
  predictionId: string;
  symbol: string;
  onClose: () => void;
  onCreated: () => void;
}

export default function CreateCaseDrawer({ open, predictionId, symbol, onClose, onCreated }: Props) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      const payload: CaseCreate = {
        prediction_snapshot_id: predictionId,
        direction: values.direction,
        thesis: values.thesis,
        expected_return_lower: values.expected_return_lower / 100,
        expected_return_upper: values.expected_return_upper / 100,
        counterargument: values.counterargument,
        invalidation_condition: values.invalidation_condition,
        planned_entry: values.planned_entry,
        target_price: values.target_price,
        stop_price: values.stop_price,
        confidence: values.confidence,
      };
      await createResearchCase(payload);
      message.success("研究案例已创建");
      form.resetFields();
      onCreated();
    } catch (e: any) {
      if (e?.response?.data?.detail) message.error(e.response.data.detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Drawer title={`新建研究案例 - ${symbol}`} open={open} onClose={onClose} width={420}>
      <Form form={form} layout="vertical" initialValues={{ direction: "BULLISH", confidence: 3 }}>
        <Form.Item name="direction" label="方向" rules={[{ required: true }]}>
          <Select options={[
            { value: "BULLISH", label: "看多" },
            { value: "NEUTRAL", label: "中性" },
            { value: "BEARISH", label: "看空" },
          ]} />
        </Form.Item>
        <Form.Item name="thesis" label="核心论点" rules={[{ required: true }]}>
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item name="expected_return_lower" label="预期收益下限(%)" rules={[{ required: true }]}>
          <InputNumber style={{ width: "100%" }} step={0.5} />
        </Form.Item>
        <Form.Item name="expected_return_upper" label="预期收益上限(%)" rules={[{ required: true }]}>
          <InputNumber style={{ width: "100%" }} step={0.5} />
        </Form.Item>
        <Form.Item name="counterargument" label="最强反驳" rules={[{ required: true }]}>
          <Input.TextArea rows={2} />
        </Form.Item>
        <Form.Item name="invalidation_condition" label="失效条件" rules={[{ required: true }]}>
          <Input.TextArea rows={2} />
        </Form.Item>
        <Form.Item name="planned_entry" label="计划入场价" rules={[{ required: true }]}>
          <InputNumber style={{ width: "100%" }} step={0.01} />
        </Form.Item>
        <Form.Item name="target_price" label="目标价" rules={[{ required: true }]}>
          <InputNumber style={{ width: "100%" }} step={0.01} />
        </Form.Item>
        <Form.Item name="stop_price" label="止损价" rules={[{ required: true }]}>
          <InputNumber style={{ width: "100%" }} step={0.01} />
        </Form.Item>
        <Form.Item name="confidence" label="信心(1-5)" rules={[{ required: true }]}>
          <InputNumber min={1} max={5} style={{ width: "100%" }} />
        </Form.Item>
        <Button type="primary" onClick={handleSubmit} loading={loading} block>
          创建案例
        </Button>
      </Form>
    </Drawer>
  );
}