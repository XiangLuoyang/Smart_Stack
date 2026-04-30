"""
Demo数据生成器 - 当所有在线数据源不可用时提供离线演示数据
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DemoDataGenerator:
    """生成逼真的模拟股票数据，用于离线演示"""

    # 预设股票元信息
    STOCK_META = {
        '000001': {'name': '平安银行', 'market': 'SZ', 'base_price': 12.50, 'volatility': 0.022},
        '000002': {'name': '万科A', 'market': 'SZ', 'base_price': 8.30, 'volatility': 0.028},
        '000858': {'name': '五粮液', 'market': 'SZ', 'base_price': 145.00, 'volatility': 0.020},
        '002415': {'name': '海康威视', 'market': 'SZ', 'base_price': 32.00, 'volatility': 0.025},
        '600519': {'name': '贵州茅台', 'market': 'SH', 'base_price': 1680.00, 'volatility': 0.018},
        '600036': {'name': '招商银行', 'market': 'SH', 'base_price': 42.00, 'volatility': 0.020},
        '600276': {'name': '恒瑞医药', 'market': 'SH', 'base_price': 48.00, 'volatility': 0.024},
        '601318': {'name': '中国平安', 'market': 'SH', 'base_price': 52.00, 'volatility': 0.019},
        '000333': {'name': '美的集团', 'market': 'SZ', 'base_price': 72.00, 'volatility': 0.021},
        '300750': {'name': '宁德时代', 'market': 'SZ', 'base_price': 205.00, 'volatility': 0.030},
    }

    def __init__(self, config=None):
        self.config = config or {}
        np.random.seed(42)  # 固定种子，保证可复现
        logger.info("Demo 数据生成器已初始化")

    def _generate_ohlcv(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """使用几何布朗运动生成逼真的OHLCV数据"""
        meta = self.STOCK_META.get(symbol, {
            'name': f'股票{symbol}', 'base_price': 50.0, 'volatility': 0.025
        })
        base_price = meta['base_price']
        annual_vol = meta['volatility']

        # 解析日期
        if len(start_date) == 8:
            start = datetime.strptime(start_date, '%Y%m%d')
        else:
            start = datetime.strptime(start_date, '%Y-%m-%d')

        if len(end_date) == 8:
            end = datetime.strptime(end_date, '%Y%m%d')
        else:
            end = datetime.strptime(end_date, '%Y-%m-%d')

        # 生成交易日序列
        dates = pd.bdate_range(start=start, end=end)
        if len(dates) == 0:
            dates = pd.bdate_range(start=start, periods=252)

        n = len(dates)
        daily_vol = annual_vol / np.sqrt(252)

        # 几何布朗运动模拟价格
        returns = np.random.normal(0.0002, daily_vol, n)  # 微小正漂移
        prices = base_price * np.exp(np.cumsum(returns))

        # 为每根K线生成 OHLC
        data = []
        for i, (d, close) in enumerate(zip(dates, prices)):
            daily_range = close * daily_vol * np.random.uniform(0.5, 2.0)
            open_price = close * (1 + np.random.normal(0, 0.005))
            high = max(open_price, close) + abs(daily_range * np.random.random() * 0.5)
            low = min(open_price, close) - abs(daily_range * np.random.random() * 0.5)
            low = max(low, 0.01)
            volume = int(abs(np.random.normal(5_000_000, 2_000_000)))

            data.append({
                'Date': d,
                'Open': round(open_price, 2),
                'High': round(high, 2),
                'Low': round(low, 2),
                'Close': round(close, 2),
                'Volume': volume,
                'Symbol': symbol,
            })

        df = pd.DataFrame(data)
        df['Date'] = pd.to_datetime(df['Date'])
        return df

    def load_stock_data(
        self, stock_code: str, period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Tuple[pd.DataFrame, str]:
        """生成模拟股票数据"""
        try:
            clean = str(stock_code).strip().upper()
            if '.' in clean:
                clean = clean.split('.')[0]

            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')

            df = self._generate_ohlcv(clean, start_date, end_date)

            if period == 'weekly':
                df = df.set_index('Date').resample('W').agg({
                    'Open': 'first', 'High': 'max', 'Low': 'min',
                    'Close': 'last', 'Volume': 'sum', 'Symbol': 'first'
                }).dropna().reset_index()
            elif period == 'monthly':
                df = df.set_index('Date').resample('ME').agg({
                    'Open': 'first', 'High': 'max', 'Low': 'min',
                    'Close': 'last', 'Volume': 'sum', 'Symbol': 'first'
                }).dropna().reset_index()

            logger.info(f"Demo 数据生成: {clean} → {len(df)} 条记录")
            return df, clean
        except Exception as e:
            logger.error(f"Demo 数据生成失败: {e}")
            return pd.DataFrame(), stock_code

    def get_market_info(self, stock_code: str) -> Dict[str, Any]:
        """返回股票市场信息"""
        clean = str(stock_code).strip().upper()
        if '.' in clean:
            clean = clean.split('.')[0]

        meta = self.STOCK_META.get(clean, {})
        market = meta.get('market', 'Unknown')
        is_sh = market == 'SH'

        return {
            'symbol': clean,
            'standardized_symbol': f"{clean}.{'SS' if is_sh else 'SZ'}",
            'name': meta.get('name', f'股票{clean}'),
            'market': market,
            'market_name': '上海证券交易所' if is_sh else '深圳证券交易所',
            'currency': 'CNY',
            'timezone': 'Asia/Shanghai',
            'exchange': 'SSE' if is_sh else 'SZSE',
            'country': 'China',
            'data_source': 'demo'
        }

    def get_real_time_quote(self, stock_code: str) -> Dict[str, Any]:
        """生成模拟实时行情"""
        clean = str(stock_code).strip().upper()
        if '.' in clean:
            clean = clean.split('.')[0]

        meta = self.STOCK_META.get(clean, {'base_price': 50.0, 'name': f'股票{clean}'})
        base = meta['base_price']
        latest = round(base * (1 + np.random.normal(0, 0.015)), 2)
        change_pct = round((latest - base) / base * 100, 2)
        pre_close = base

        return {
            'symbol': clean,
            'name': meta.get('name', f'股票{clean}'),
            'latest_price': latest,
            'change_percent': change_pct,
            'change_amount': round(latest - pre_close, 2),
            'volume': int(abs(np.random.normal(5_000_000, 2_000_000))),
            'amount': round(latest * abs(np.random.normal(5_000_000, 2_000_000)), 0),
            'open': round(pre_close * (1 + np.random.normal(0, 0.005)), 2),
            'high': round(max(latest, pre_close) * (1 + abs(np.random.normal(0, 0.01))), 2),
            'low': round(min(latest, pre_close) * (1 - abs(np.random.normal(0, 0.01))), 2),
            'pre_close': pre_close,
            'amplitude': round(abs(np.random.normal(3, 1)), 2),
            'turnover_rate': round(abs(np.random.normal(2, 0.8)), 2),
            'pe_ratio': round(abs(np.random.normal(20, 8)), 2),
            'pb_ratio': round(abs(np.random.normal(3, 1.5)), 2),
            'timestamp': datetime.now().isoformat(),
            'data_source': 'demo'
        }

    def test_connection(self) -> bool:
        """Demo数据源始终可用"""
        return True
