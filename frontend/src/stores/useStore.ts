import { create } from "zustand";
import type { Account, AccountOverview, Order, PlaceOrderResult, Quote, RiskRule, Trade } from "../types";
import * as api from "../api/client";

interface AppState {
  // 璐︽埛
  accounts: Account[];
  currentAccountId: string | null;
  overview: AccountOverview | null;
  loadAccounts: () => Promise<void>;
  selectAccount: (id: string) => void;
  refreshOverview: () => Promise<void>;

  // 鑷€?+ 褰撳墠閫変腑鏍囩殑
  watchlist: string[];
  currentSymbol: string | null;
  loadWatchlist: () => Promise<void>;
  selectSymbol: (s: string) => void;
  addSymbol: (s: string) => Promise<void>;
  removeSymbol: (s: string) => Promise<void>;

  // 琛屾儏缂撳瓨
  quotes: Record<string, Quote>;
  setQuote: (q: Quote) => void;
  setQuotes: (qs: Quote[]) => void;
  refreshQuotes: () => Promise<void>;

  // 璁㈠崟 / 鎴愪氦
  orders: Order[];
  trades: Trade[];
  loadOrders: () => Promise<void>;
  loadTrades: () => Promise<void>;

  // 椋庢帶
  riskRule: RiskRule | null;
  loadRiskRule: () => Promise<void>;

  // 涓嬪崟(杩斿洖鍚庣缁撴灉,鐢辩粍浠跺鐞嗘秷鎭彁绀?
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
  quotes: {},
  orders: [],
  trades: [],
  riskRule: null,

  loadAccounts: async () => {
    const accounts = await api.listAccounts();
    set({ accounts });
    // 自动选第一个账户
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
  },

  selectSymbol: (s) => set({ currentSymbol: s }),

  addSymbol: async (s) => {
    const watchlist = await api.addToWatchlist(s);
    set({ watchlist });
  },

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
    // 涓嬪崟鍚庡埛鏂拌处鎴?+ 璁㈠崟
    await Promise.all([get().refreshOverview(), get().loadOrders(), get().loadTrades()]);
    return result;
  },
}));