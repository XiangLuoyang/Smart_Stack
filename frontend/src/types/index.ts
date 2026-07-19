// 与后端 Pydantic schema 对齐的类型

export interface Account {
  id: string;
  name: string;
  cash: number;
  status: string;
  created_at: string;
}

export interface Position {
  symbol: string;
  qty: number;
  avg_cost: number;
  last_price: number | null;
  market_value: number;
  profit: number;
  profit_pct: number;
  stop_loss_price: number | null;
  take_profit_price: number | null;
}

export interface AccountOverview {
  account_id: string;
  name: string;
  cash: number;
  status: string;
  positions: Position[];
  total_market_value: number;
  total_cost: number;
  total_assets: number;
  floating_profit: number;
  floating_profit_pct: number;
  updated_at: string;
}

export type Side = "BUY" | "SELL";
export type OrderType = "MARKET" | "LIMIT";
export type OrderStatus = "PENDING" | "FILLED" | "CANCELLED" | "REJECTED";

export interface Order {
  id: string;
  account_id: string;
  symbol: string;
  side: Side;
  order_type: OrderType;
  qty: number;
  price: number | null;
  filled_qty: number;
  filled_price: number | null;
  status: OrderStatus;
  reject_reason: string | null;
  created_at: string;
  filled_at: string | null;
}

export interface Trade {
  id: string;
  order_id: string;
  account_id: string;
  symbol: string;
  side: Side;
  qty: number;
  price: number;
  commission: number;
  stamp_duty: number;
  transfer_fee: number;
  total_cost: number;
  filled_at: string;
}

export interface PlaceOrderResult {
  accepted: boolean;
  message: string;
  order: Order | null;
  trade: Trade | null;
}

export interface Quote {
  symbol: string;
  price: number;
  ts: string;
  bid: number | null;
  ask: number | null;
  prev_close: number | null;
  change_pct: number | null;
}

export interface KlineBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ma5: number | null;
  ma20: number | null;
  ma60: number | null;
}

export interface RiskRule {
  account_id: string;
  max_position_pct: number;
  max_single_pct: number;
  stop_loss_pct: number;
  take_profit_pct: number;
  max_daily_trades: number;
}

export interface SignalPayload {
  score: number;
  created_at: string;
  [k: string]: unknown;
}

export interface SignalOut {
  symbol: string;
  lstm: SignalPayload | null;
  llm: SignalPayload | null;
}

export interface BacktestRun {
  id: string;
  strategy_name: string;
  params_json: string;
  start: string;
  end: string;
  metrics_json: string;
  equity_curve_json: string | null;
  created_at: string;
}
