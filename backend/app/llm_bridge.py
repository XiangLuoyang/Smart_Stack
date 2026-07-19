"""LLM 桥接:封装旧 src/llm_analysis/core.py,统一错误处理。

把 CrewAI 调用收敛到一处,失败时返回空字符串而不是抛异常,
避免阻塞下单链路(API 层不应依赖 LLM 可用性)。
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def generate_llm_report(symbol: str) -> str:
    """生成 LLM 分析报告,失败返回空串。

    调用旧 src/llm_analysis/core.py,如果 LLM_API_KEY 未配置则跳过。
    """
    import os

    if not os.getenv("LLM_API_KEY"):
        logger.info("LLM_API_KEY 未配置,跳过 LLM 报告生成")
        return ""

    try:
        from src.llm_analysis.core import create_financial_analysis_crew, StockAnalysisReport

        crew = create_financial_analysis_crew(symbol)
        result = crew.kickoff()
        # CrewAI 返回 CrewOutput,有 raw / str() 两种取法
        report_text = getattr(result, "raw", None) or str(result)
        return report_text or ""
    except Exception as e:
        logger.warning(f"LLM 报告生成失败 {symbol}: {e}")
        return ""
