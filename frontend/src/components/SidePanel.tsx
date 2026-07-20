import { Empty, Table, Tag, Typography } from "antd";
import { useStore } from "../stores/useStore";
import SymbolTag from "./SymbolTag";

const { Text, Title } = Typography;

export default function SidePanel() {
  const overview = useStore((s) => s.overview);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <div style={{ padding: "10px 12px 6px" }}>
        <Text style={{ color: "#9ba8b8", fontSize: 11, letterSpacing: 0.5 }}>持仓</Text>
      </div>
      <div style={{ flex: 1, overflow: "auto", padding: "0 4px" }}>
        <Table
          size="small"
          rowKey="symbol"
          dataSource={overview?.positions ?? []}
          pagination={false}
          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无持仓" /> }}
          columns={[
            {
              title: "标的",
              dataIndex: "symbol",
              width: 110,
              render: (_: unknown, r: any) => <SymbolTag code={r.symbol} showCode={false} />,
            },
            { title: "数量", dataIndex: "qty", width: 64, align: "right" as const, render: (v: number) => v.toFixed(0) },
            { title: "成本", dataIndex: "avg_cost", width: 64, align: "right" as const, render: (v: number) => v.toFixed(2) },
            { title: "现价", dataIndex: "last_price", width: 64, align: "right" as const, render: (v: number | null) => v?.toFixed(2) ?? "--" },
            {
              title: "盈亏",
              width: 96,
              align: "right" as const,
              render: (_: unknown, r: any) => {
                const p = r.profit as number;
                const pct = (r.profit_pct as number) * 100;
                const c = p >= 0 ? "#ef5350" : "#26a69a";
                return (
                  <span style={{ color: c, fontSize: 12 }}>
                    {p >= 0 ? "+" : ""}
                    {p.toFixed(0)}
                    <br />
                    <span style={{ fontSize: 11 }}>
                      ({pct >= 0 ? "+" : ""}
                      {pct.toFixed(2)}%)
                    </span>
                  </span>
                );
              },
            },
          ]}
        />
      </div>
    </div>
  );
}