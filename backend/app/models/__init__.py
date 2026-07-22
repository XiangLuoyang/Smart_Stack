"""ORM 模型聚合导入,确保 Base.metadata 能收集到所有表。"""
from app.models.account import Account
from app.models.position import Position
from app.models.order import Order
from app.models.trade import Trade
from app.models.risk_rule import RiskRule
from app.models.market_snapshot import MarketSnapshot
from app.models.signal import Signal
from app.models.backtest import BacktestRun, BacktestTrade
from app.models.forecast import (
    MarketDataBatch,
    DailyBar,
    UniverseSnapshot,
    TradingCalendar,
    ModelVersion,
    ScreeningRun,
    ScreeningCandidate,
    PredictionSnapshot,
    ReviewResult,
)
from app.models.settlement_lot import SettlementLot
from app.models.order_reservation import OrderReservation
from app.models.research import (
    ResearchCase,
    EvidenceEntry,
    DecisionEntry,
    ReviewNote,
)

__all__ = [
    "Account",
    "Position",
    "Order",
    "Trade",
    "RiskRule",
    "MarketSnapshot",
    "Signal",
    "BacktestRun",
    "BacktestTrade",
    "MarketDataBatch",
    "DailyBar",
    "UniverseSnapshot",
    "TradingCalendar",
    "ModelVersion",
    "ScreeningRun",
    "ScreeningCandidate",
    "PredictionSnapshot",
    "ReviewResult",
    "ResearchCase",
    "EvidenceEntry",
    "DecisionEntry",
    "ReviewNote",
]