import { useEffect, useState } from "react";
import { Layout, Typography } from "antd";
import AppNavigation from "./components/AppNavigation";
import TodayPage from "./pages/TodayPage";
import ScreenerPage from "./pages/ScreenerPage";
import StockResearchPage from "./pages/StockResearchPage";
import ResearchCasesPage from "./pages/ResearchCasesPage";
import ReviewCenterPage from "./pages/ReviewCenterPage";
import OperationsPage from "./pages/OperationsPage";
import PerformancePage from "./pages/PerformancePage";
import { useStore } from "./stores/useStore";
import type { NavigationState, WorkspacePage } from "./types";

const { Sider, Content } = Layout;
const { Text } = Typography;

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div style={{ padding: 24 }}>
      <Text style={{ color: "#8b949e" }}>{title} - 尚未启用</Text>
    </div>
  );
}

export default function App() {
  const [nav, setNav] = useState<NavigationState>({ page: "today" });
  const currentSymbol = useStore((s) => s.currentSymbol);

  const navigate = (page: WorkspacePage) => setNav({ page });

  useEffect(() => {
    if (currentSymbol && nav.page === "screener") {
      setNav({ page: "stock", symbol: currentSymbol });
    }
  }, [currentSymbol]);

  const renderPage = () => {
    switch (nav.page) {
      case "today":
        return <TodayPage />;
      case "screener":
        return <ScreenerPage />;
      case "stock":
        return <StockResearchPage symbol={nav.symbol} />;
      case "cases":
        return <ResearchCasesPage />;
      case "reviews":
        return <ReviewCenterPage />;
      case "performance":
        return <PlaceholderPage title="模型表现" />;
      case "operations":
        return <PlaceholderPage title="模拟操作" />;
      case "settings":
        return <PlaceholderPage title="设置" />;
      default:
        return <TodayPage />;
    }
  };

  return (
    <Layout style={{ height: "100vh", overflow: "hidden", background: "#0b0e14" }}>
      <Sider width={180} theme="dark" style={{ background: "#0e1117", borderRight: "1px solid #21262d", overflow: "auto" }}>
        <AppNavigation current={nav} onNavigate={navigate} />
      </Sider>
      <Content style={{ overflow: "hidden", background: "#0b0e14" }}>
        {renderPage()}
      </Content>
    </Layout>
  );
}