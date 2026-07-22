import { Menu, Divider } from "antd";
import {
  CalendarOutlined,
  FundOutlined,
  SearchOutlined,
  FileTextOutlined,
  AuditOutlined,
  LineChartOutlined,
  SettingOutlined,
  ExperimentOutlined,
} from "@ant-design/icons";
import type { NavigationState, WorkspacePage } from "../types";

interface Props {
  current: NavigationState;
  onNavigate: (page: WorkspacePage) => void;
}

const primaryItems = [
  { key: "today", icon: <CalendarOutlined />, label: "今日" },
  { key: "screener", icon: <FundOutlined />, label: "沪深300" },
  { key: "stock", icon: <SearchOutlined />, label: "单股研究" },
  { key: "cases", icon: <FileTextOutlined />, label: "研究案例" },
  { key: "reviews", icon: <AuditOutlined />, label: "复盘" },
  { key: "performance", icon: <LineChartOutlined />, label: "模型表现" },
];

const secondaryItems = [
  { key: "operations", icon: <ExperimentOutlined />, label: "模拟操作" },
  { key: "settings", icon: <SettingOutlined />, label: "设置" },
];

export default function AppNavigation({ current, onNavigate }: Props) {
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "12px 16px 8px", fontWeight: 700, fontSize: 15, color: "#e6edf3" }}>
        Smart Stack
      </div>
      <Menu
        mode="inline"
        theme="dark"
        selectedKeys={[current.page]}
        onClick={({ key }) => onNavigate(key as WorkspacePage)}
        items={primaryItems}
        style={{ border: "none", background: "transparent" }}
      />
      <Divider style={{ margin: "8px 16px", minWidth: "auto" }} />
      <Menu
        mode="inline"
        theme="dark"
        selectedKeys={[current.page]}
        onClick={({ key }) => onNavigate(key as WorkspacePage)}
        items={secondaryItems}
        style={{ border: "none", background: "transparent" }}
      />
    </div>
  );
}