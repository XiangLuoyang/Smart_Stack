"""LLM 桥接:直接调用 OpenAI 兼容接口(DeepSeek 等)生成分析报告。

不依赖 CrewAI 多智能体框架,避免版本兼容问题(system_prompt 参数冲突)。
报告内容基于实时技术指标 + 近期 K 线走势,失败时返回空串,不阻塞下单链路。
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "你是一位专注 A 股市场的量化分析师。请基于给定的技术指标与近期行情, "
    "用清晰、客观的中文撰写一份简短的投资参考报告。包含:趋势判断、关键价位、 "
    "风险提示与操作建议。报告为 Markdown 格式, 不超过 400 字, "
    "并在结尾明确标注「本报告由 AI 生成, 仅作参考, 不构成投资建议」。"
)


def _gather_context(symbol: str) -> str:
    """拉取最近 K 线 + 技术指标, 组装成供 LLM 阅读的文本。"""
    try:
        from app.db.base import SessionLocal
        from app.services.market_service import MarketService

        db = SessionLocal()
        try:
            market = MarketService(db)
            df = market.get_kline(symbol, days=60)
            if df.empty:
                return f"(暂无 {symbol} 行情数据)"
            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) >= 2 else last
            close = float(last.get("Close", 0))
            prev_close = float(prev.get("Close", close))
            chg = (close - prev_close) / prev_close * 100 if prev_close else 0

            # 近 20 日统计
            recent = df.tail(20)
            high20 = float(recent["High"].max())
            low20 = float(recent["Low"].min())
            vol_avg = float(recent["Volume"].mean()) if "Volume" in recent else 0

            def _f(v):
                try:
                    return round(float(v), 3) if v == v else None
                except Exception:
                    return None

            parts = [
                f"股票代码: {symbol}",
                f"最新收盘: {round(close, 2)} 元 (前收 {round(prev_close, 2)}, 涨跌 {round(chg, 2)}%)",
                f"近20日最高/最低: {round(high20, 2)} / {round(low20, 2)}",
                f"近20日平均成交量: {int(vol_avg)}",
                f"MA5={_f(last.get('MA5'))} MA20={_f(last.get('MA20'))} MA60={_f(last.get('MA60'))}",
                f"RSI(14)={_f(last.get('RSI'))}",
                f"MACD={_f(last.get('MACD'))} 信号线={_f(last.get('Signal_Line'))} 柱={_f(last.get('MACD_Histogram'))}",
                f"布林带上={_f(last.get('BB_Upper'))} 中={_f(last.get('BB_Middle'))} 下={_f(last.get('BB_Lower'))}",
            ]
            # 近 5 日收盘序列, 帮助判断短期趋势
            tail5 = [round(float(x), 2) for x in df["Close"].tail(5).tolist()]
            parts.append(f"近5日收盘序列: {tail5}")
            return "\n".join(parts)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"组装 LLM 上下文失败 {symbol}: {e}")
        return f"(组装 {symbol} 上下文失败: {e})"


def generate_llm_report(symbol: str) -> str:
    """生成 LLM 分析报告, 失败返回空串。"""
    if not os.getenv("LLM_API_KEY"):
        logger.info("LLM_API_KEY 未配置, 跳过 LLM 报告生成")
        return ""

    base_url = os.getenv("LLM_API_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("LLM_MODEL_NAME", "deepseek-chat")
    # .env 里 model 可能写成 "deepseek/deepseek-chat" (litellm 风格), OpenAI 接口要去掉前缀
    if "/" in model:
        model = model.split("/", 1)[1]

    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("LLM_API_KEY"), base_url=base_url)
        ctx = _gather_context(symbol)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"请基于以下数据对 {symbol} 做分析:\n\n{ctx}"},
            ],
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
            max_tokens=800,
            timeout=90,
        )
        report = (resp.choices[0].message.content or "").strip()
        logger.info(f"LLM 报告生成成功 {symbol}: {len(report)} 字")
        return report
    except Exception as e:
        logger.warning(f"LLM 报告生成失败 {symbol}: {e}")
        return ""