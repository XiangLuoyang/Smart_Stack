import { useEffect, useRef, useState } from "react";
import { Alert, Button, Empty, InputNumber, Progress, Space, Spin, Tag, Tooltip, Typography, message } from "antd";
import { getScreenerStatus, startScreener, type ScreenerItem, type ScreenerStatus } from "../api/client";
import { useStore } from "../stores/useStore";
import SymbolTag from "./SymbolTag";

const { Text } = Typography;

function fmtPct(v: number | null | undefined, dp = 2): string {
  if (v == null || Number.isNaN(v)) return "--";
  return (v * 100).toFixed(dp) + "%";
}

/** One ranked row: name (SymbolTag) + annualized return + 95% CI bar. */
function RankRow({ item, rank, kind }: { item: ScreenerItem; rank: number; kind: "buy" | "sell" }) {
  const selectSymbol = useStore((s) => s.selectSymbol);
  const up = kind === "buy";
  const color = up ? "#ef5350" : "#26a69a";
  const ci = item.ci;
  return (
    <div
      onClick={() => selectSymbol(item.code)}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "6px 8px",
        borderBottom: "1px solid #21262d",
        cursor: "pointer",
      }}
      title="点击查看该标的详情"
    >
      <Text style={{ color: "#6e7681", fontSize: 11, width: 16, fontFamily: "ui-monospace, monospace" }}>{rank}</Text>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          <SymbolTag code={item.code} showCode={false} strongName />
          <span style={{ color: "#6e7681", fontSize: 10, marginLeft: 6 }}>{item.code}</span>
        </div>
        {ci && (
          <Text style={{ color: "#6e7681", fontSize: 10 }}>
            95% CI {fmtPct(ci.lower)} ~ {fmtPct(ci.upper)}
          </Text>
        )}
      </div>
      <Tag color={up ? "red" : "green"} style={{ margin: 0, fontFamily: "ui-monospace, monospace", fontWeight: 600 }}>
        {up ? "▲" : "▼"} {fmtPct(item.score)}
      </Tag>
    </div>
  );
}

export default function ScreenerPanel() {
  const [status, setStatus] = useState<ScreenerStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [topN, setTopN] = useState(10);
  const loadSymbolNames = useStore((s) => s.loadSymbolNames);
  const timer = useRef<number | null>(null);

  // pull status on mount (picks up last result from disk if backend restarted)
  const poll = (once = false) => {
    getScreenerStatus()
      .then((s) => {
        setStatus(s);
        // prefetch names for whatever is in the result so rows render with company names
        const codes = [
          ...(s.result?.buy ?? []),
          ...(s.result?.sell ?? []),
        ].map((i) => i.code);
        if (codes.length) void loadSymbolNames(codes);
        if (!once && s.running) {
          timer.current = window.setTimeout(() => poll(), 2500);
        }
      })
      .catch(() => {
        if (!once) message.error("选股状态查询失败");
      });
  };

  useEffect(() => {
    poll(true);
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const doScan = async () => {
    setLoading(true);
    try {
      const s = await startScreener(topN);
      setStatus(s);
      message.success(s.action === "already_running" ? "扫描进行中..." : "沪深300选股已启动");
      poll();
    } catch (e: any) {
      message.error("启动失败:" + (e?.message ?? e));
    } finally {
      setLoading(false);
    }
  };

  const running = status?.running;
  const done = status?.progress_done ?? 0;
  const total = status?.progress_total ?? 0;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  const res = status?.result;

  return (
    <div style={{ padding: "8px 12px", overflow: "auto", height: "100%" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <Text style={{ color: "#9ba8b8", fontSize: 12 }}>沪深300 全成分股扫描</Text>
        <Space size={6}>
          <InputNumber
            size="small"
            min={1}
            max={50}
            value={topN}
            onChange={(v) => setTopN(v ?? 10)}
            style={{ width: 64 }}
            disabled={!!running}
          />
          <Tooltip title="遍历 300 只成分股,逐只计算预期年化收益,耗时约数分钟">
            <Button size="small" type="primary" loading={loading || !!running} onClick={doScan}>
              开始扫描
            </Button>
          </Tooltip>
        </Space>
      </div>

      {/* progress */}
      {(running || (total > 0 && !res)) && (
        <div style={{ background: "#0e1117", borderRadius: 4, padding: 10, marginBottom: 8, border: "1px solid #21262d" }}>
          <Progress percent={pct} size="small" strokeColor="#2f6fde" />
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#6e7681", marginTop: 4 }}>
            <span>
              {done} / {total}
            </span>
            <span style={{ fontFamily: "ui-monospace, monospace" }}>{status?.current_symbol || "等待..."}</span>
          </div>
        </div>
      )}

      {status?.error && (
        <Alert type="error" message="扫描出错" description={status.error} style={{ marginBottom: 8, fontSize: 11 }} />
      )}

      {!running && !res && !status?.error && (
        <div style={{ padding: 24, textAlign: "center" }}>
          <Empty description="尚未扫描,点击「开始扫描」" />
        </div>
      )}

      {res && (
        <Spin spinning={false}>
          <Text style={{ color: "#6e7681", fontSize: 11 }}>
            已评分 {res.scored_count} / {res.pool_size} · {res.finished_at?.slice(0, 16).replace("T", " ")}
          </Text>

          <div style={{ background: "#0e1117", borderRadius: 4, padding: "2px 0", marginTop: 6, marginBottom: 8, border: "1px solid #21262d" }}>
            <div style={{ padding: "6px 8px", borderBottom: "1px solid #21262d" }}>
              <Tag color="red" style={{ margin: 0 }}>买入 Top {res.buy.length}</Tag>
            </div>
            {res.buy.length === 0 ? (
              <div style={{ padding: 10, color: "#6e7681", fontSize: 12 }}>无数据</div>
            ) : (
              res.buy.map((it, i) => <RankRow key={it.code} item={it} rank={i + 1} kind="buy" />)
            )}
          </div>

          <div style={{ background: "#0e1117", borderRadius: 4, padding: "2px 0", border: "1px solid #21262d" }}>
            <div style={{ padding: "6px 8px", borderBottom: "1px solid #21262d" }}>
              <Tag color="green" style={{ margin: 0 }}>卖出 Top {res.sell.length}</Tag>
            </div>
            {res.sell.length === 0 ? (
              <div style={{ padding: 10, color: "#6e7681", fontSize: 12 }}>无数据</div>
            ) : (
              res.sell.map((it, i) => <RankRow key={it.code} item={it} rank={i + 1} kind="sell" />)
            )}
          </div>
        </Spin>
      )}

      <Alert
        type="warning"
        message="排名基于历史收益统计的年化预期,仅为筛选参考,不构成投资建议"
        style={{ marginTop: 8, fontSize: 11 }}
      />
    </div>
  );
}