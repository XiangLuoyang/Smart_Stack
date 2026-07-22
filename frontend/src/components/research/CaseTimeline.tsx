import { Timeline, Tag, Typography } from "antd";
import type { DecisionEntry, EvidenceEntry, ReviewNote } from "../../types";

const { Text } = Typography;

interface Props {
  evidence: EvidenceEntry[];
  decisions: DecisionEntry[];
  reviews: ReviewNote[];
}

const STANCE_COLOR: Record<string, string> = { SUPPORT: "green", OPPOSE: "red", NEUTRAL: "default" };
const DIRECTION_COLOR: Record<string, string> = { BULLISH: "green", BEARISH: "red", NEUTRAL: "default" };

interface TimelineItem {
  ts: string;
  color: string;
  content: React.ReactNode;
}

export default function CaseTimeline({ evidence, decisions, reviews }: Props) {
  const items: TimelineItem[] = [];

  for (const e of evidence) {
    items.push({
      ts: e.created_at,
      color: STANCE_COLOR[e.stance] ?? "gray",
      content: (
        <div>
          <Tag color={STANCE_COLOR[e.stance]}>{e.stance}</Tag>
          <Tag>{e.category}</Tag>
          <Text style={{ color: "#e6edf3" }}>{e.content}</Text>
          {e.source_label && <Text style={{ color: "#8b949e", marginLeft: 8 }}>({e.source_label})</Text>}
        </div>
      ),
    });
  }

  for (const d of decisions) {
    items.push({
      ts: d.created_at,
      color: DIRECTION_COLOR[d.direction] ?? "blue",
      content: (
        <div>
          <Tag color={DIRECTION_COLOR[d.direction]}>{d.direction}</Tag>
          <Tag color="blue">{d.action}</Tag>
          <Text style={{ color: "#e6edf3" }}>{d.rationale}</Text>
          <Text style={{ color: "#8b949e", marginLeft: 8 }}>信心: {d.confidence}/5</Text>
        </div>
      ),
    });
  }

  for (const r of reviews) {
    items.push({
      ts: r.created_at,
      color: "purple",
      content: (
        <div>
          <Tag color="purple">复盘</Tag>
          <Text style={{ color: "#e6edf3" }}>{r.content}</Text>
        </div>
      ),
    });
  }

  items.sort((a, b) => a.ts.localeCompare(b.ts));

  if (items.length === 0) {
    return <Text style={{ color: "#8b949e" }}>暂无事件</Text>;
  }

  return (
    <Timeline
      items={items.map((item) => ({
        color: item.color,
        children: (
          <div>
            <Text style={{ color: "#6e7681", fontSize: 11 }}>{item.ts.replace("T", " ").slice(0, 19)}</Text>
            <div>{item.content}</div>
          </div>
        ),
      }))}
    />
  );
}