import { useState } from "react";
import { Form, Input, Select, Switch, Button, message } from "antd";
import http from "../../api/client";

const ERROR_TAGS = [
  "MODEL_DIRECTION", "MODEL_MAGNITUDE", "THESIS", "TIMING",
  "EARLY_ENTRY", "LATE_ENTRY", "EARLY_EXIT", "LATE_EXIT",
  "DISCIPLINE", "DATA_QUALITY",
];

interface Props {
  predictionId: string;
  onSubmitted: () => void;
}

export default function ReviewForm({ predictionId, onSubmitted }: Props) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      await http.post(`/reviews/${predictionId}/notes`, {
        attribution: values.attribution,
        error_tags: values.error_tags ?? [],
        discipline_followed: values.discipline_followed ?? null,
      });
      message.success("复盘笔记已提交");
      form.resetFields();
      onSubmitted();
    } catch (e: any) {
      if (e?.response?.data?.detail) message.error(String(e.response.data.detail));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form form={form} layout="vertical" initialValues={{ discipline_followed: true }}>
      <Form.Item name="attribution" label="归因分析" rules={[{ required: true, message: "请输入归因" }]}>
        <Input.TextArea rows={3} placeholder="方向正确但进场过早..." />
      </Form.Item>
      <Form.Item name="error_tags" label="误差标签">
        <Select mode="multiple" options={ERROR_TAGS.map((t) => ({ value: t, label: t }))} placeholder="选择标签" />
      </Form.Item>
      <Form.Item name="discipline_followed" label="是否遵守纪律" valuePropName="checked">
        <Switch checkedChildren="是" unCheckedChildren="否" />
      </Form.Item>
      <Button type="primary" onClick={handleSubmit} loading={loading} block>提交复盘</Button>
    </Form>
  );
}