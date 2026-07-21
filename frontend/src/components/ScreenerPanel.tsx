import { useEffect, useState } from "react";
import { Alert, Empty, Segmented, Spin, Tag, Typography, message } from "antd";
import { getScreenerRun, listScreenerRuns } from "../api/client";
import { useStore } from "../stores/useStore";
import type { ScreeningCandidate, ScreeningRun } from "../types";
import SymbolTag from "./SymbolTag";

const { Text } = Typography;

function fmtPct(v: number | null | undefined, dp = 2): string {
  if (v == null || Number.isNaN(v)) return "--";
  return (v * 100).toFixed(dp) + "%";
}

const STATUS_COLOR: Record<string, string> = {
  SUCCESS: "green",
  PARTIAL: "orange",
  FAILED: "red",
};

/** 单个候选行:成功显示排名+预期超额,失败显示原因标签。 */
function CandidateRow({ c }: { c: ScreeningCandidate }) {
  const selectSymbol = useStore((s) => s.selectSymbol);
  const success = c.status === "SUCCESS";
  return (
    <div
      onClick={() => selectSymbol(c.symbol)}
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
      <Text style={{ color: "#6e7681", fontSize: 11, width: 20, fontFamily: "ui-monospace, monospace" }}>
        {success ? c.rank : "-"}
      </Text>
      <div style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        <SymbolTag code={c.symbol} showCode={false} strongName />
        <span style={{ color: "#6e7681", fontSize: 10, marginLeft: 6 }}>{c.symbol}</span>
      </div>
      {success ? (
        <Tag color="red" style={{ margin: 0, fontFamily: "ui-monospace, monospace", fontWeight: 600 }}>
          {fmtPct(c.score)}
        </Tag>
      ) : (
        <Tag color="default" style={{ margin: 0, fontSize: 10 }}>
          {c.failure_reason ?? "FAILED"}
        </Tag>
      )}
    </div>
  );
}

export default function ScreenerPanel() {
  const [run, setRun] = useState<ScreeningRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState<"top10" | "success" | "all">("top10");
  const loadSymbolNames = useStore((s) => s.loadSymbolNames);

  useEffect(() => {
    setLoading(true);
    listScreenerRuns({ limit: 1 })
      .then((runs) => {
        if (runs.length === 0) {
          setRun(null);
          return;
        }
        return getScreenerRun(runs[0].id).then((full) => {
          setRun(full);
          const codes = full.candidates.map((c) => c.symbol);
          if (codes.length) void loadSymbolNames(codes);
        });
      })
      .catch(() => message.error("筛选运行加载失败"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const rows: ScreeningCandidate[] = run
    ? view === "top10"
      ? run.top10
      : view === "success"
        ? run.candidates.filter((c) => c.status === "SUCCESS")
        : run.candidates
    : [];

  return (
    <div style={{ padding: "8px 12px", overflow: "auto", height: "100%" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <Text style={{ color: "#9ba8b8", fontSize: 12 }}>沪深300 研究筛选</Text>
        {run && (
          <Tag color={STATUS_COLOR[run.status] ?? "default"} style={{ margin: 0 }}>
            {run.status}
          </Tag>
        )}
      </div>

      {loading && (
        <div style={{ textAlign: "center", padding: 24 }}>
          <Spin />
        </div>
      )}

      {!loading && !run && (
        <div style={{ padding: 24, textAlign: "center" }}>
          <Empty description="尚无筛选运行,等待每日 16:30 自动研究或手动触发" />
        </div>
      )}

      {!loading && run && (
        <>
          <div
            style={{
              background: "#0e1117",
              border: "1px solid #21262d",
              borderRadius: 6,
              padding: 10,
              marginBottom: 8,
              fontSize: 11,
              color: "#6e7681",
            }}
          >
            <div>
              业务日 <Text style={{ color: "#c9d1d9" }}>{run.business_date}</Text> · 模型{" "}
              <Text style={{ color: "#c9d1d9" }}>{run.model_version ?? run.model_version_id}</Text>
            </div>
            <div style={{ marginTop: 4 }}>
              数据截止{" "}
              <Text style={{ color: "#c9d1d9" }}>
                {run.data_cutoff ? run.data_cutoff.slice(0, 16).replace("T", " ") : "--"}
              </Text>{" "}
              · 成功 <Text style={{ color: "#ef5350" }}>{run.success_count}</Text> / 失败{" "}
              <Text style={{ color: "#6e7681" }}>{run.failure_count}</Text> / 共{" "}
              <Text style={{ color: "#c9d1d9" }}>{run.total_count}</Text>
            </div>
          </div>

          <Segmented
            size="small"
            value={view}
            onChange={(v) => setView(v as typeof view)}
            options={[
              { label: "Top 10", value: "top10" },
              { label: "全部成功", value: "success" },
              { label: "含失败", value: "all" },
            ]}
            style={{ marginBottom: 8 }}
          />

          <div style={{ background: "#0e1117", borderRadius: 4, padding: "2px 0", border: "1px solid #21262d" }}>
            {rows.length === 0 ? (
              <div style={{ padding: 10, color: "#6e7681", fontSize: 12 }}>无数据</div>
            ) : (
              rows.map((c) => <CandidateRow key={c.id} c={c} />)
            )}
          </div>

          <Alert
            type="warning"
            message="排名基于 10 日预期超额收益,仅为研究参考,不构成投资建议"
            style={{ marginTop: 8, fontSize: 11 }}
          />
        </>
      )}
    </div>
  );
}