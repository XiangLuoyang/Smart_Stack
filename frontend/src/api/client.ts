import axios from "axios";
import type {
  Account,
  AccountOverview,
  BacktestRun,
  KlineBar,
  Order,
  PlaceOrderResult,
  Quote,
  RiskRule,
  SignalOut,
  Trade,
} from "../types";

const http = axios.create({
  baseURL: "/api",
  timeout: 30000,
});

// 账户
export const listAccounts = () => http.get<Account[]>("/accounts").then((r) => r.data);
export const createAccount = (name: string, initial_cash: number) =>
  http.post<Account>("/accounts", { name, initial_cash }).then((r) => r.data);
export const getAccountOverview = (id: string) =>
  http.get<AccountOverview>(`/accounts/${id}`).then((r) => r.data);
export const listTrades = (account_id?: string) =>
  http
    .get<Trade[]>("/orders/trades", { params: { account_id } })
    .then((r) => r.data);

// 订单
export interface PlaceOrderPayload {
  account_id: string;
  symbol: string;
  side: "BUY" | "SELL";
  qty: number;
  order_type: "MARKET" | "LIMIT";
  price?: number | null;
}
export const placeOrder = (p: PlaceOrderPayload) =>
  http.post<PlaceOrderResult>("/orders", p).then((r) => r.data);
export const cancelOrder = (id: string) =>
  http.delete(`/orders/${id}`).then((r) => r.data);
export const listOrders = (params: { account_id?: string; status?: string }) =>
  http.get<Order[]>("/orders", { params }).then((r) => r.data);

// 行情
export const getQuotes = (symbols: string[]) =>
  http.get<Quote[]>("/quotes", { params: { symbols: symbols.join(",") } }).then((r) => r.data);
export const refreshQuotes = (symbols: string[]) =>
  http
    .post("/market/refresh", null, { params: { symbols: symbols.join(",") } })
    .then((r) => r.data);
export const getKline = (symbol: string, days = 120) =>
  http
    .get<KlineBar[]>("/market/kline", { params: { symbol, days } })
    .then((r) => r.data);

// 信号
export const getSignal = (symbol: string) =>
  http.get<SignalOut>(`/signals/${symbol}`).then((r) => r.data);
export const refreshSignal = (symbol: string, source = "ALL") =>
  http
    .post("/signals/refresh", null, { params: { symbol, source } })
    .then((r) => r.data);

// 风控
export const getRiskRule = (account_id: string) =>
  http.get<RiskRule>(`/risk-rules/${account_id}`).then((r) => r.data);
export const updateRiskRule = (account_id: string, payload: Partial<RiskRule>) =>
  http.put<RiskRule>(`/risk-rules/${account_id}`, payload).then((r) => r.data);

// 回测
export const runBacktest = (payload: {
  symbol: string;
  strategy_name: string;
  params: Record<string, unknown>;
  start: string;
  end: string;
  initial_cash?: number;
}) => http.post<BacktestRun>("/backtest/run", payload).then((r) => r.data);
export const listBacktestRuns = () =>
  http.get<BacktestRun[]>("/backtest/runs").then((r) => r.data);
export const getBacktestRun = (id: string) =>
  http.get<BacktestRun>(`/backtest/runs/${id}`).then((r) => r.data);

// 自选股
export const listWatchlist = () =>
  http.get<string[]>("/watchlist").then((r) => r.data);
export const addToWatchlist = (symbol: string) =>
  http.post<string[]>("/watchlist", { symbol }).then((r) => r.data);
export const removeFromWatchlist = (symbol: string) =>
  http.delete<string[]>(`/watchlist/${symbol}`).then((r) => r.data);

export default http;
