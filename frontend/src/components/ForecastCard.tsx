import { Tag, Typography } from "antd";
import type { ForecastSnapshot } from "../types";

const { Text } = Typography;

function fmtPct(v: number | null | undefined, dp = 2): string {
  if (v == null || Number.isNaN(v)) return "--";
  return (v * 100).toFixed(dp) + "%";
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Text style={{ color: "#6e7681", fontSize: 10 }}>{label}</Text>
      <Text
        style={{
          color: color ?? "#c9d1d9",
          fontSize: 13,
          fontFamily: "ui-monospace, monospace",
          fontWeight: 600,
        }}
      >
        {value}
      </Text>
    </div>
  );
}

const STATE_COLOR: Record<string, string> = {
  PENDING: "blue",
  PENDING_DATA: "orange",
  SETTLED: "green",
};

/** 纯数值预测卡片:展示 10 日中位/区间/概率/超额,不混入 LLM 文本评分。 */
export default function ForecastCard({ forecast }: { forecast: ForecastSnapshot }) {
  const f = forecast;
  const up = "#ef5350";
  const down = "#26a69a";
  return (
    <div style={{ background: "#0e1117", border: "1px solid #21262d", borderRadius: 6, padding: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <Text style={{ color: "#9ba8b8", fontSize: 12 }}>
          {f.business_date} · {f.horizon_days} 日预测
        </Text>
        <Tag color={STATE_COLOR[f.state] ?? "default"} style={{ margin: 0 }}>
          {f.state}
        </Tag>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
        <Stat label="中位收益" value={fmtPct(f.median_return)} color={f.median_return >= 0 ? up : down} />
        <Stat label="预期超额" value={fmtPct(f.expected_excess_return)} color={f.expected_excess_return >= 0 ? up : down} />
        <Stat label="收益区间" value={`${fmtPct(f.lower_return)} ~ ${fmtPct(f.upper_return)}`} />
        <Stat label="上涨概率" value={fmtPct(f.p_up)} color={up} />
        <Stat label="持平概率" value={fmtPct(f.p_flat)} />
        <Stat label="下跌概率" value={fmtPct(f.p_down)} color={down} />
        <Stat label="预期 MFE" value={fmtPct(f.expected_mfe)} color={up} />
        <Stat label="预期 MAE" value={fmtPct(f.expected_mae)} color={down} />
      </div>
    </div>
  );
}