import { useEffect } from "react";
import { Layout, message } from "antd";
import WorkbenchHeader from "./components/WorkbenchHeader";
import WatchlistPanel from "./components/WatchlistPanel";
import MainPanel from "./components/MainPanel";
import SidePanel from "./components/SidePanel";
import BottomTabs from "./components/BottomTabs";
import { useStore } from "./stores/useStore";
import { useQuoteStream } from "./hooks/useQuoteStream";

const { Header, Sider, Content, Footer } = Layout;

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

  // 初次加载:账户 + 自选
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

  // 切账户时重新拉数据
  useEffect(() => {
    if (!currentAccountId) return;
    (async () => {
      await Promise.all([
        refreshOverview(),
        loadOrders(),
        loadTrades(),
        loadRiskRule(),
      ]);
    })();
  }, [currentAccountId]);

  // 行情轮询(每 10 秒,SSE 兜底)
  useEffect(() => {
    const t = setInterval(refreshQuotes, 10_000);
    return () => clearInterval(t);
  }, [refreshQuotes]);

  return (
    <Layout style={{ height: "100vh", overflow: "hidden" }}>
      <Header style={{ height: 48, lineHeight: "48px", padding: "0 16px" }}>
        <WorkbenchHeader />
      </Header>
      <Layout>
        <Sider width={240} theme="light" style={{ overflow: "auto", background: "#f5f5f5" }}>
          <WatchlistPanel />
        </Sider>
        <Content style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <MainPanel />
          <BottomTabs />
        </Content>
        <Sider width={360} theme="light" style={{ overflow: "auto", background: "#f5f5f5" }}>
          <SidePanel />
        </Sider>
      </Layout>
    </Layout>
  );
}
