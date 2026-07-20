import { AutoComplete, Button, List, Popconfirm, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { useStore } from "../stores/useStore";
import { searchSymbols, type SymbolInfo } from "../api/client";
import SymbolTag from "./SymbolTag";

const { Text } = Typography;

export default function WatchlistPanel() {
  const watchlist = useStore((s) => s.watchlist);
  const quotes = useStore((s) => s.quotes);
  const currentSymbol = useStore((s) => s.currentSymbol);
  const selectSymbol = useStore((s) => s.selectSymbol);
  const addSymbol = useStore((s) => s.addSymbol);
  const removeSymbol = useStore((s) => s.removeSymbol);
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<{ value: string; label: React.ReactNode }[]>([]);
  const [searching, setSearching] = useState(false);

  // debounce search -> backend /symbols/search
  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setOptions([]);
      return;
    }
    let cancelled = false;
    setSearching(true);
    const t = setTimeout(async () => {
      try {
        const hits: SymbolInfo[] = await searchSymbols(q);
        if (cancelled) return;
        setOptions(
          hits.map((h) => ({
            value: h.code,
            label: (
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>
                  <Text style={{ color: "#e6edf3" }}>{h.name}</Text>
                  <Text style={{ color: "#6e7681", fontSize: 11, marginLeft: 8 }}>{h.code}</Text>
                </span>
              </div>
            ),
          })),
        );
      } catch {
        /* ignore */
      } finally {
        if (!cancelled) setSearching(false);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [query]);

  const handleAdd = (code: string) => {
    const c = code.trim();
    if (!c) return;
    void addSymbol(c);
    setQuery("");
    setOptions([]);
  };

  return (
    <div style={{ padding: 8, height: "100%", display: "flex", flexDirection: "column", gap: 8 }}>
      <AutoComplete
        style={{ width: "100%" }}
        size="small"
        value={query}
        options={options}
        onChange={setQuery}
        onSelect={(v) => handleAdd(String(v))}
        placeholder={searching ? "搜索中..." : "搜索代码 / 名称 加入自选"}
        notFoundContent={query && !searching ? "无匹配" : undefined}
        allowClear
      />
      <div style={{ flex: 1, overflow: "auto", margin: "0 -4px" }}>
        <List
          size="small"
          dataSource={watchlist}
          locale={{ emptyText: "暂无自选,请在上方搜索添加" }}
          renderItem={(symbol) => {
            const q = quotes[symbol];
            const change = q?.change_pct;
            const color =
              change == null ? "#6e7681" : change > 0 ? "#ef5350" : change < 0 ? "#26a69a" : "#6e7681";
            const selected = symbol === currentSymbol;
            return (
              <List.Item
                style={{
                  padding: "8px 10px",
                  margin: "0 4px",
                  borderRadius: 4,
                  background: selected ? "#1c2230" : "transparent",
                  borderLeft: selected ? "3px solid #2f7bff" : "3px solid transparent",
                  cursor: "pointer",
                }}
                onClick={() => selectSymbol(symbol)}
                actions={[
                  <Popconfirm
                    key="rm"
                    title="移出自选?"
                    onConfirm={(e) => {
                      e?.stopPropagation();
                      void removeSymbol(symbol);
                    }}
                  >
                    <Button type="text" size="small" danger onClick={(e) => e.stopPropagation()}>
                      ×
                    </Button>
                  </Popconfirm>,
                ]}
              >
                <div style={{ display: "flex", justifyContent: "space-between", width: "100%", paddingRight: 4 }}>
                  <div style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
                    <SymbolTag code={symbol} showCode={false} strongName />
                    <Text style={{ color: "#6e7681", fontSize: 11 }}>{symbol}</Text>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ color, fontSize: 14, fontWeight: 600 }}>
                      {q ? q.price.toFixed(2) : "--"}
                    </div>
                    {change != null && (
                      <Tag
                        color={change > 0 ? "red" : change < 0 ? "green" : "default"}
                        style={{ margin: 0, fontSize: 11 }}
                      >
                        {change >= 0 ? "+" : ""}
                        {change.toFixed(2)}%
                      </Tag>
                    )}
                  </div>
                </div>
              </List.Item>
            );
          }}
        />
      </div>
    </div>
  );
}
