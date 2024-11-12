from datetime import datetime, time
from typing import Optional

def is_trading_hours() -> bool:
    """判断当前是否为A股交易时间"""
    current_time = datetime.now().time()
    
    for period in DataConfig.TRADING_HOURS.values():
        if period[0] <= current_time <= period[1]:
            return True
    return False

def format_stock_code(code: str) -> str:
    """格式化股票代码"""
    if not code.endswith('.SZ'):
        code = code + '.SZ'
    return code.upper()

def format_number(number: float, decimals: int = 2) -> str:
    """格式化数字"""
    return f"{number:,.{decimals}f}"
