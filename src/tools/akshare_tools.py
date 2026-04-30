"""
AKShare数据工具 - 为LLM提供A股实时数据
"""

import pandas as pd
from datetime import datetime, timedelta
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import json
import os

# 禁用代理
os.environ.setdefault('no_proxy', '*')
os.environ.setdefault('NO_PROXY', '*')


class StockInput(BaseModel):
    """Input schema for AKShareStockTool."""
    symbol: str = Field(..., description="The stock symbol (e.g., '000001', '600519')")


class AKShareStockTool(BaseTool):
    """使用AKShare获取A股实时数据的工具"""
    name: str = "stock_data_tool"
    description: str = """
    获取A股实时和历史市场数据的工具。
    用于获取：
    - 最新股票价格和交易日期
    - 成交量和成交额
    - 52周最高/最低价
    - 市值、市盈率、市净率等财务指标
    - 公司基本信息
    """
    args_schema: type[BaseModel] = StockInput

    def _run(self, symbol: str) -> str:
        try:
            import akshare as ak

            # 标准化股票代码
            code = str(symbol).strip().upper()
            if '.' in code:
                code = code.split('.')[0]

            # 获取实时行情
            try:
                spot_df = ak.stock_zh_a_spot_em()
                stock_data = spot_df[spot_df['代码'] == code]
            except:
                # 备用方案：使用历史数据接口
                spot_df = None
                stock_data = None

            # 获取历史数据（用于52周高低点）
            try:
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')

                # 添加市场前缀
                if code.startswith(('0', '3')):
                    symbol_with_prefix = f"sz{code}"
                else:
                    symbol_with_prefix = f"sh{code}"

                hist_df = ak.stock_zh_a_daily(symbol=symbol_with_prefix)
                hist_df['date'] = pd.to_datetime(hist_df['date'])

                # 过滤最近一年数据
                one_year_ago = datetime.now() - timedelta(days=365)
                hist_df = hist_df[hist_df['date'] >= one_year_ago]

            except Exception as e:
                hist_df = None

            # 获取公司信息
            try:
                info_df = ak.stock_individual_info_em(symbol=code)
                company_info = {}
                for _, row in info_df.iterrows():
                    company_info[row['item']] = row['value']
            except:
                company_info = {}

            # 构建响应
            response = {}

            # 基本信息
            response["company_name"] = company_info.get('股票简称', stock_data['名称'].values[0] if stock_data is not None and len(stock_data) > 0 else code)
            response["symbol"] = code

            # 最新交易数据
            if stock_data is not None and len(stock_data) > 0:
                stock = stock_data.iloc[0]
                response["latest_trading_data"] = {
                    "date": datetime.now().strftime('%Y-%m-%d'),
                    "price": float(stock['最新价']) if pd.notna(stock['最新价']) else None,
                    "open_price": float(stock['今开']) if pd.notna(stock['今开']) else None,
                    "volume": float(stock['成交量']) if pd.notna(stock['成交量']) else None,
                    "amount": float(stock['成交额']) if pd.notna(stock['成交额']) else None,
                    "change_percent": f"{float(stock['涨跌幅']):.2f}%" if pd.notna(stock['涨跌幅']) else "N/A",
                    "high": float(stock['最高']) if pd.notna(stock['最高']) else None,
                    "low": float(stock['最低']) if pd.notna(stock['最低']) else None,
                }
            elif hist_df is not None and len(hist_df) > 0:
                # 使用历史数据最新一条
                latest = hist_df.iloc[-1]
                response["latest_trading_data"] = {
                    "date": latest['date'].strftime('%Y-%m-%d'),
                    "price": float(latest['close']) if pd.notna(latest['close']) else None,
                    "open_price": float(latest['open']) if pd.notna(latest['open']) else None,
                    "volume": float(latest['volume']) if pd.notna(latest['volume']) else None,
                    "amount": float(latest['amount']) if pd.notna(latest['amount']) else None,
                }
            else:
                response["latest_trading_data"] = {"error": "无法获取实时数据"}

            # 52周数据
            if hist_df is not None and len(hist_df) > 0:
                response["52_week_high"] = {
                    "price": float(hist_df['high'].max()) if pd.notna(hist_df['high'].max()) else None,
                    "date": hist_df.loc[hist_df['high'].idxmax(), 'date'].strftime('%Y-%m-%d') if pd.notna(hist_df['high'].max()) else "N/A"
                }
                response["52_week_low"] = {
                    "price": float(hist_df['low'].min()) if pd.notna(hist_df['low'].min()) else None,
                    "date": hist_df.loc[hist_df['low'].idxmin(), 'date'].strftime('%Y-%m-%d') if pd.notna(hist_df['low'].min()) else "N/A"
                }

            # 财务指标
            response["market_cap"] = company_info.get('总市值', 'N/A')
            response["pe_ratio"] = company_info.get('市盈率-动态', 'N/A')
            response["pb_ratio"] = company_info.get('市净率', 'N/A')
            response["eps"] = company_info.get('每股收益', 'N/A')
            response["dividend_yield"] = company_info.get('股息率', 'N/A')
            response["beta"] = company_info.get('贝塔系数', 'N/A')

            # 业务摘要
            response["business_summary"] = company_info.get('主营业务', 'N/A')

            # 添加数据源和时间戳
            response["data_source"] = "AKShare (新浪财经)"
            response["fetch_time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            return json.dumps(response, indent=2, ensure_ascii=False)

        except Exception as e:
            return json.dumps({
                "error": f"获取数据失败: {str(e)}",
                "symbol": symbol,
                "data_source": "AKShare",
                "fetch_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, indent=2, ensure_ascii=False)

    async def _arun(self, symbol: str) -> str:
        return self._run(symbol)
