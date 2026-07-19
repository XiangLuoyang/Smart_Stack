import { Button, Input, List, Popconfirm, Space, Tag, Typography } from "antd";
import { useState } from "react";
import { useStore } from "../stores/useStore";

const { Text } = Typography;

export default function WatchlistPanel() {
  const watchlist = useStore((s) => s.watchlist);
  const quotes = useStore((s) => s.quotes);
  const currentSymbol = useStore((s) => s.currentSymbol);
  const selectSymbol = useStore((s) => s.selectSymbol);
  const addSymbol = useStore((s) => s.addSymbol);
  const removeSymbol = useStore((s) => s.removeSymbol);
  const [input, setInput] = useState("");

  const handleAdd = async () => {
    const code = input.trim();
    if (!code) return;
    await addSymbol(code);
    setInput("");
  };

  return (
    <div style={{ padding: 8, height: "100%", display: "flex", flexDirection: "column" }}>
      <Space.Compact style={{ width: "100%", marginBottom: 8 }}>
        <Input
          size="small"
          placeholder="代码如 000001"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={handleAdd}
        />
        <Button size="small" type="primary" onClick={handleAdd}>+</Button>
      </Space.Compact>

      <div style={{ flex: 1, overflow: "auto" }}>
        <List
          size="small"
          dataSource={watchlist}
          locale={{ emptyText: "暂无自选,输入代码添加" }}
          renderItem={(symbol) => {
            const q = quotes[symbol];
            const change = q?.change_pct;
            const color =
              change == null ? "#666" : change > 0 ? "#f5222d" : change < 0 ? "#52c41a" : "#666";
            const selected = symbol === currentSymbol;
            return (
              <List.Item
                style={{
                  padding: "6px 8px",
                  background: selected ? "#e6f4ff" : undefined,
                  cursor: "pointer",
                  borderLeft: selected ? "3px solid #1677ff" : "3px solid transparent",
                }}
                onClick={() => selectSymbol(symbol)}
                actions={[
                  <Popconfirm
                    key="rm"
                    title="移除?"
                    onConfirm={() => removeSymbol(symbol)}
                  >
                    <Button type="link" size="small" danger>×</Button>
                  </Popconfirm>,
                ]}
              >
                <Space direction="vertical" size={0} style={{ width: "100%" }}>
                  <Text strong>{symbol}</Text>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <Text style={{ color, fontSize: 14, fontWeight: 600 }}>
                      {q ? q.price.toFixed(2) : "--"}
                    </Text>
                    {change != null && (
                      <Tag color={change > 0 ? "red" : change < 0 ? "green" : "default"} style={{ margin: 0 }}>
                        {change >= 0 ? "+" : ""}{change.toFixed(2)}%
                      </Tag>
                    )}
                  </div>
                </Space>
              </List.Item>
            );
          }}
        />
      </div>
    </div>
  );
}
