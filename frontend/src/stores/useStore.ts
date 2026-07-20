import { create } from "zustand";
import type { Account, AccountOverview, Order, PlaceOrderResult, Quote, RiskRule, Trade } from "../types";
import * as api from "../api/client";

interface AppState {
  // 账户
  accounts: Account[];
  currentAccountId: string | null;
  overview: AccountOverview | null;
  loadAccounts: () => Promise<void>;
  selectAccount: (id: string) => void;
  refreshOverview: () => Promise<void>;

  // 自�?+ 当前选中标的
  watchlist: string[];
  currentSymbol: string | null;
  symbolNames: Record<string, string>;
  loadWatchlist: () => Promise<void>;
  selectSymbol: (s: string) => void;
  addSymbol: (s: string) => Promise<void>;
  removeSymbol: (s: string) => Promise<void>;
  loadSymbolNames: (codes: string[]) => Promise<void>;
  setSymbolName: (code: string, name: string) => void;

  // 行情缓存
  quotes: Record<string, Quote>;
  setQuote: (q: Quote) => void;
  setQuotes: (qs: Quote[]) => void;
  refreshQuotes: () => Promise<void>;

  // 订单 / 成交
  orders: Order[];
  trades: Trade[];
  loadOrders: () => Promise<void>;
  loadTrades: () => Promise<void>;

  // 风控
  riskRule: RiskRule | null;
  loadRiskRule: () => Promise<void>;

  // 下单(返回后端结果,由组件处理消息提�?
  placeOrder: (
    p: Omit<api.PlaceOrderPayload, "account_id">
  ) => Promise<PlaceOrderResult | null>;
}

export const useStore = create<AppState>((set, get) => ({
  accounts: [],
  currentAccountId: null,
  overview: null,
  watchlist: [],
  currentSymbol: null,
  symbolNames: {},
  quotes: {},
  orders: [],
  trades: [],
  riskRule: null,

  loadAccounts: async () => {
    const accounts = await api.listAccounts();
    set({ accounts });
    // �Զ�ѡ��һ���˻�
    const cur = get().currentAccountId;
    if (!cur && accounts.length > 0) {
      set({ currentAccountId: accounts[0].id });
    }
  },

  selectAccount: (id) => {
    set({ currentAccountId: id, overview: null, orders: [], trades: [], riskRule: null });
  },

  refreshOverview: async () => {
    const id = get().currentAccountId;
    if (!id) return;
    const overview = await api.getAccountOverview(id);
    set({ overview });
  },

  loadWatchlist: async () => {
    const watchlist = await api.listWatchlist();
    set({ watchlist });
    if (!get().currentSymbol && watchlist.length > 0) {
      set({ currentSymbol: watchlist[0] });
    }
    if (watchlist.length > 0) {
      void get().loadSymbolNames(watchlist);
    }
  },

  selectSymbol: (s) => set({ currentSymbol: s }),

  addSymbol: async (s) => {
    const watchlist = await api.addToWatchlist(s);
    set({ watchlist });
    void get().loadSymbolNames([s]);
  },

  loadSymbolNames: async (codes) => {
    if (codes.length === 0) return;
    const need = codes.filter((c) => !get().symbolNames[c]);
    if (need.length === 0) return;
    try {
      const names = await api.getSymbolNames(need);
      set((st) => ({ symbolNames: { ...st.symbolNames, ...names } }));
    } catch {
      /* name lookup should never block the UI */
    }
  },

  setSymbolName: (code, name) =>
    set((st) => ({ symbolNames: { ...st.symbolNames, [code]: name } })),

  removeSymbol: async (s) => {
    const watchlist = await api.removeFromWatchlist(s);
    set({ watchlist });
    if (get().currentSymbol === s) {
      set({ currentSymbol: watchlist[0] ?? null });
    }
  },

  setQuote: (q) =>
    set((st) => ({ quotes: { ...st.quotes, [q.symbol]: q } })),
  setQuotes: (qs) =>
    set((st) => {
      const next = { ...st.quotes };
      for (const q of qs) next[q.symbol] = q;
      return { quotes: next };
    }),

  refreshQuotes: async () => {
    const wl = get().watchlist;
    if (wl.length === 0) return;
    const fresh = await api.getQuotes(wl);
    get().setQuotes(fresh);
  },

  loadOrders: async () => {
    const id = get().currentAccountId;
    if (!id) return;
    const orders = await api.listOrders({ account_id: id });
    set({ orders });
  },

  loadTrades: async () => {
    const id = get().currentAccountId;
    if (!id) return;
    const trades = await api.listTrades(id);
    set({ trades });
  },

  loadRiskRule: async () => {
    const id = get().currentAccountId;
    if (!id) return;
    try {
      const rule = await api.getRiskRule(id);
      set({ riskRule: rule });
    } catch {
      set({ riskRule: null });
    }
  },

  placeOrder: async (p) => {
    const account_id = get().currentAccountId;
    if (!account_id) return null;
    const result = await api.placeOrder({ ...p, account_id });
    // 下单后刷新账�?+ 订单
    await Promise.all([get().refreshOverview(), get().loadOrders(), get().loadTrades()]);
    return result;
  },
}));
