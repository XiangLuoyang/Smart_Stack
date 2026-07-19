"""纯计算引擎层:无 IO、无状态、可独立测试。

这里只放纯函数式的业务计算(费用、撮合、风控规则判断),
对外部资源(数据库、行情源、LLM)的访问由 services/ 层负责。
"""
from app.engine.fees import FeesCalculator, FeeBreakdown
from app.engine.matching import MatchingEngine, MatchResult
from app.engine.risk import RiskEngine, RiskCheckResult

__all__ = [
    "FeesCalculator",
    "FeeBreakdown",
    "MatchingEngine",
    "MatchResult",
    "RiskEngine",
    "RiskCheckResult",
]
