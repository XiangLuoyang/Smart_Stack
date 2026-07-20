import React from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import App from "./App";
import "./index.css";

// Pro trading dark theme: deep navy base, cyan accent, red/green for A-share up/down
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: "#2f7bff",
          colorInfo: "#2f7bff",
          colorBgBase: "#0e1117",
          colorBgContainer: "#161b22",
          colorBgElevated: "#1c2230",
          colorBgLayout: "#0b0e14",
          colorBorder: "#2a313c",
          colorBorderSecondary: "#21262d",
          colorTextBase: "#e6edf3",
          colorTextSecondary: "#9ba8b8",
          colorSuccess: "#26a69a",
          colorError: "#ef5350",
          colorWarning: "#ffb547",
          borderRadius: 4,
          fontSize: 13,
          controlHeight: 28,
        },
        components: {
          Layout: {
            headerBg: "#0b0e14",
            bodyBg: "#0b0e14",
            siderBg: "#0e1117",
            headerHeight: 48,
            headerPadding: "0 16px",
          },
          Card: { colorBgContainer: "#161b22", headerBg: "transparent", headerFontSize: 13 },
          Table: {
            headerBg: "#1c2230",
            headerColor: "#9ba8b8",
            rowHoverBg: "#1c2230",
            borderColor: "#21262d",
            cellPaddingBlock: 6,
            cellPaddingInline: 8,
          },
          Tabs: { itemActiveColor: "#e6edf3", titleFontSize: 13 },
          Input: { colorBgContainer: "#0e1117" },
          InputNumber: { colorBgContainer: "#0e1117" },
          Select: { colorBgContainer: "#0e1117", optionSelectedBg: "#1c2230" },
          Modal: { contentBg: "#161b22", headerBg: "#161b22" },
          Statistic: { titleFontSize: 11, contentFontSize: 16 },
          Tag: { defaultBg: "#1c2230", defaultColor: "#9ba8b8" },
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>
);
