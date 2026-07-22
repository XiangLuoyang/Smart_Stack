import { useState } from "react";
import { Form, Input, Select, Button, message } from "antd";
import { appendEvidence } from "../../api/client";

interface Props {
  caseId: string;
  onAppended: () => void;
}

export default function EvidenceForm({ caseId, onAppended }: Props) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      await appendEvidence(caseId, {
        stance: values.stance,
        category: values.category,
        content: values.content,
        source_label: values.source_label || undefined,
        observed_date: values.observed_date,
      });
      message.success("证据已追加");
      form.resetFields();
      onAppended();
    } catch (e: any) {
      if (e?.response?.data?.detail) message.error(e.response.data.detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form form={form} layout="inline" style={{ marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
      <Form.Item name="stance" rules={[{ required: true }]} style={{ marginBottom: 0 }}>
        <Select placeholder="立场" style={{ width: 100 }} options={[
          { value: "SUPPORT", label: "支持" },
          { value: "OPPOSE", label: "反对" },
          { value: "NEUTRAL", label: "中立" },
        ]} />
      </Form.Item>
      <Form.Item name="category" rules={[{ required: true }]} style={{ marginBottom: 0 }}>
        <Input placeholder="类别" style={{ width: 100 }} />
      </Form.Item>
      <Form.Item name="content" rules={[{ required: true }]} style={{ marginBottom: 0, flex: 1 }}>
        <Input placeholder="内容" />
      </Form.Item>
      <Form.Item name="source_label" style={{ marginBottom: 0 }}>
        <Input placeholder="来源" style={{ width: 80 }} />
      </Form.Item>
      <Form.Item name="observed_date" rules={[{ required: true }]} style={{ marginBottom: 0 }}>
        <Input placeholder="观察日期 YYYY-MM-DD" style={{ width: 140 }} />
      </Form.Item>
      <Button type="primary" size="small" onClick={handleSubmit} loading={loading}>追加证据</Button>
    </Form>
  );
}