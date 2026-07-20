import { useEffect } from "react";
import { Layout, message, Tabs } from "antd";
import WorkbenchHeader from "./components/WorkbenchHeader";
import WatchlistPanel from "./components/WatchlistPanel";
import MainPanel from "./components/MainPanel";
import SidePanel from "./components/SidePanel";
import AnalysisPanel from "./components/AnalysisPanel";
import BottomTabs from "./components/BottomTabs";
import ScreenerPanel from "./components/ScreenerPanel";
import { useStore } from "./stores/useStore";
import { useQuoteStream } from "./hooks/useQuoteStream";

const { Header, Sider, Content } = Layout;

export default function App() {
  const loadAccounts = useStore((s) => s.loadAccounts);
  const loadWatchlist = useStore((s) => s.loadWatchlist);
  const currentAccountId = useStore((s) => s.currentAccountId);
  const refreshOverview = useStore((s) => s.refreshOverview);
  const loadOrders = useStore((s) => s.loadOrders);
  const loadTrades = useStore((s) => s.loadTrades);
  const loadRiskRule = useStore((s) => s.loadRiskRule);
  const refreshQuotes = useStore((s) => s.refreshQuotes);

  useQuoteStream();

  // initial load: accounts + watchlist
  useEffect(() => {
    (async () => {
      try {
        await loadAccounts();
        await loadWatchlist();
      } catch (e: any) {
        message.error("初始化失败:" + (e?.message ?? e));
      }
    })();
  }, []);

  // re-fetch on account switch
  useEffect(() => {
    if (!currentAccountId) return;
    (async () => {
      await Promise.all([refreshOverview(), loadOrders(), loadTrades(), loadRiskRule()]);
    })();
  }, [currentAccountId]);

  // quote polling fallback (every 10s, alongside SSE)
  useEffect(() => {
    const t = setInterval(refreshQuotes, 10_000);
    return () => clearInterval(t);
  }, [refreshQuotes]);

  return (
    <Layout style={{ height: "100vh", overflow: "hidden", background: "#0b0e14" }}>
      <Header style={{ height: 48, lineHeight: "48px", padding: 0, background: "#0b0e14" }}>
        <WorkbenchHeader />
      </Header>
      <Layout style={{ background: "#0b0e14" }}>
        <Sider width={240} theme="dark" style={{ overflow: "hidden", background: "#0e1117", borderRight: "1px solid #21262d" }}>
          <div style={{ padding: "8px 0 0", color: "#6e7681", fontSize: 11, paddingLeft: 12 }}>自选</div>
          <WatchlistPanel />
        </Sider>

        <Content style={{ display: "flex", flexDirection: "column", overflow: "hidden", background: "#0b0e14" }}>
          <MainPanel />
          <BottomTabs />
        </Content>

        <Sider width={360} theme="dark" style={{ overflow: "hidden", background: "#0e1117", borderLeft: "1px solid #21262d", height: "100%" }}>
          <Tabs
            size="small"
            defaultActiveKey="analysis"
            className="ant-tabs-fill-height"
            style={{ padding: "0 4px" }}
            tabBarStyle={{ margin: 0, padding: "0 8px" }}
            items={[
              { key: "analysis", label: "分析", children: <AnalysisPanel /> },
              { key: "screener", label: "选股", children: <ScreenerPanel /> },
              { key: "positions", label: "持仓", children: <SidePanel /> },
            ]}
          />
        </Sider>
      </Layout>
    </Layout>
  );
}
