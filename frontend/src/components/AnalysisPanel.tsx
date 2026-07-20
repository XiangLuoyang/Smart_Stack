import { Alert, Button, Empty, Space, Spin, Tag, Tooltip, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { getIndicators, getSignal, refreshSignal, type IndicatorReport } from "../api/client";
import { useStore } from "../stores/useStore";
import SymbolTag from "./SymbolTag";
import type { SignalOut } from "../types";
import ReactMarkdown from "react-markdown";

const { Text, Title } = Typography;

function fmt(v: number | null | undefined, dp = 2): string {
  if (v == null || Number.isNaN(v)) return "--";
  return v.toFixed(dp);
}

/** A single indicator row with a colored strength bar. */
function Indicator({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid #21262d" }}>
      <Text style={{ color: "#9ba8b8", fontSize: 12 }}>
        {label}
        {hint && <Tooltip title={hint}><span style={{ color: "#6e7681", marginLeft: 4 }}>ⓘ</span></Tooltip>}
      </Text>
      <Text style={{ color: "#e6edf3", fontSize: 12, fontFamily: "ui-monospace, monospace" }}>{value}</Text>
    </div>
  );
}

export default function AnalysisPanel() {
  const currentSymbol = useStore((s) => s.currentSymbol);
  const [ind, setInd] = useState<IndicatorReport | null>(null);
  const [signal, setSignal] = useState<SignalOut | null>(null);
  const [loadingInd, setLoadingInd] = useState(false);
  const [loadingSig, setLoadingSig] = useState(false);

  useEffect(() => {
    if (!currentSymbol) {
      setInd(null);
      setSignal(null);
      return;
    }
    setLoadingInd(true);
    getIndicators(currentSymbol, 120)
      .then(setInd)
      .catch(() => setInd(null))
      .finally(() => setLoadingInd(false));
    getSignal(currentSymbol).then(setSignal).catch(() => setSignal(null));
  }, [currentSymbol]);

  const doRefresh = async (source: "LSTM" | "LLM" | "ALL") => {
    if (!currentSymbol) return;
    setLoadingSig(true);
    try {
      await refreshSignal(currentSymbol, source);
      const fresh = await getSignal(currentSymbol);
      setSignal(fresh);
      // also refresh indicators since they share kline data
      const freshInd = await getIndicators(currentSymbol, 120);
      setInd(freshInd);
      message.success("分析已刷新");
    } finally {
      setLoadingSig(false);
    }
  };

  if (!currentSymbol) {
    return (
      <div style={{ padding: 24, textAlign: "center" }}>
        <Empty description="请从左侧选择标的" />
      </div>
    );
  }

  const indData = ind?.indicators;
  const buySignals = ind?.signals?.filter((s) => s.tag === "buy") ?? [];
  const sellSignals = ind?.signals?.filter((s) => s.tag === "sell") ?? [];

  return (
    <div style={{ padding: "8px 12px", overflow: "auto", height: "100%" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <SymbolTag code={currentSymbol} strongName />
        <Space size={4}>
          <Button size="small" loading={loadingSig} onClick={() => doRefresh("LSTM")}>LSTM</Button>
          <Button size="small" loading={loadingSig} onClick={() => doRefresh("LLM")}>LLM</Button>
          <Button size="small" type="primary" loading={loadingSig} onClick={() => doRefresh("ALL")}>刷新</Button>
        </Space>
      </div>

      {/* 综合信号灯 */}
      <div style={{ background: "#0e1117", borderRadius: 4, padding: 10, marginBottom: 8, border: "1px solid #21262d" }}>
        <Text style={{ color: "#9ba8b8", fontSize: 11 }}>综合信号</Text>
        <div style={{ marginTop: 6 }}>
          {buySignals.length === 0 && sellSignals.length === 0 ? (
            <Tag color="default">中性</Tag>
          ) : (
            <Space size={4} wrap>
              {buySignals.map((s, i) => (
                <Tooltip key={i} title={s.detail}>
                  <Tag color="red" style={{ margin: 0 }}>{s.name} ▲</Tag>
                </Tooltip>
              ))}
              {sellSignals.map((s, i) => (
                <Tooltip key={i} title={s.detail}>
                  <Tag color="green" style={{ margin: 0 }}>{s.name} ▼</Tag>
                </Tooltip>
              ))}
            </Space>
          )}
        </div>
      </div>

      {/* LSTM 预期收益 */}
      <div style={{ background: "#0e1117", borderRadius: 4, padding: 10, marginBottom: 8, border: "1px solid #21262d" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Tooltip title="基于历史收益率统计的年化预期收益(95% 置信区间)。TensorFlow 未安装时使用统计方法,安装后启用 LSTM。">
            <Text style={{ color: "#9ba8b8", fontSize: 11 }}>
              预期年化收益 <span style={{ color: "#6e7681" }}>ⓘ</span>
            </Text>
          </Tooltip>
          {signal?.lstm ? (
            <Text style={{ fontSize: 18, fontWeight: 700, color: (signal.lstm.score ?? 0) >= 0 ? "#ef5350" : "#26a69a" }}>
              {((signal.lstm.score ?? 0) * 100).toFixed(2)}%
            </Text>
          ) : (
            <Text style={{ color: "#6e7681", fontSize: 12 }}>未生成</Text>
          )}
        </div>
        {signal?.lstm && (
          <div style={{ marginTop: 4, fontSize: 11, color: "#6e7681", display: "flex", justifyContent: "space-between" }}>
            <span>
              {signal.lstm.method === "lstm" ? "LSTM 模型" : "统计方法"} · 日均{" "}
              {(((signal.lstm as any).expected_daily_return ?? 0) * 100).toFixed(3)}%
            </span>
            {(signal.lstm as any).confidence_interval && (
              <span>
                95% CI [{((((signal.lstm as any).confidence_interval.lower) ?? 0) * 100).toFixed(2)}%,
                {((((signal.lstm as any).confidence_interval.upper) ?? 0) * 100).toFixed(2)}%]
              </span>
            )}
          </div>
        )}
      </div>

      {/* 技术指标 */}
      <Spin spinning={loadingInd}>
        <div style={{ background: "#0e1117", borderRadius: 4, padding: "4px 10px", marginBottom: 8, border: "1px solid #21262d" }}>
          <Text style={{ color: "#9ba8b8", fontSize: 11 }}>技术指标</Text>
          {!ind?.ready ? (
            <div style={{ padding: 8, color: "#6e7681", fontSize: 12 }}>{ind?.reason ?? "加载中..."}</div>
          ) : (
            <div style={{ marginTop: 4 }}>
              <Indicator label="RSI(14)" value={fmt(indData?.rsi ?? null, 1)} hint="<30 超卖, >70 超买" />
              <Indicator label="MACD" value={fmt(indData?.macd ?? null, 3)} />
              <Indicator label="信号线" value={fmt(indData?.macd_signal ?? null, 3)} />
              <Indicator label="MACD 柱" value={fmt(indData?.macd_hist ?? null, 3)} />
              <Indicator label="MA5 / MA20 / MA60" value={`${fmt(indData?.ma5)} / ${fmt(indData?.ma20)} / ${fmt(indData?.ma60)}`} />
              <Indicator label="布林带上/中/下" value={`${fmt(indData?.bb_upper)} / ${fmt(indData?.bb_middle)} / ${fmt(indData?.bb_lower)}`} />
              {indData?.kdj && (
                <Indicator label="KDJ (K/D/J)" value={`${fmt(indData.kdj.k, 1)} / ${fmt(indData.kdj.d, 1)} / ${fmt(indData.kdj.j, 1)}`} />
              )}
            </div>
          )}
        </div>
      </Spin>

      {/* LLM 报告 */}
      <div style={{ background: "#0e1117", borderRadius: 4, padding: 10, border: "1px solid #21262d" }}>
        <Text style={{ color: "#9ba8b8", fontSize: 11 }}>AI 分析报告 (DeepSeek)</Text>
        {signal?.llm?.report_markdown ? (
          <div style={{ fontSize: 12, marginTop: 6, color: "#c9d1d9", lineHeight: 1.7 }} className="llm-report">
            <ReactMarkdown>{String(signal.llm.report_markdown)}</ReactMarkdown>
          </div>
        ) : (
          <div style={{ padding: "12px 0" }}>
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="点击 LLM 按钮生成" />
          </div>
        )}
        <Alert
          type="warning"
          message="信号与报告仅作参考,不构成投资建议,不自动下单"
          style={{ marginTop: 8, fontSize: 11 }}
        />
      </div>
    </div>
  );
}
