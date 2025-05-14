import yfinance as yf
from datetime import datetime
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import json

class StockInput(BaseModel):
    """Input schema for YFinanceStockTool."""
    symbol: str = Field(..., description="The stock symbol to analyze (e.g., 'AAPL', 'GOOGL')")

class YFinanceStockTool(BaseTool):
    name: str = "stock_data_tool"
    description: str = """
    A tool for getting real-time and historical stock market data.
    Use this tool when you need specific stock information like:
    - Latest stock price from most recent trading day
    - Current price and trading volume
    - Historical price data
    - Company financials and metrics
    - Company information and business summary
    """
    args_schema: type[BaseModel] = StockInput

    def _run(self, symbol: str) -> str:
        try:
            stock = yf.Ticker(symbol)
            
            # Get basic info
            info = stock.info
            
            # Get recent market data
            hist = stock.history(period="1mo")
            
            # Get the latest trading day's data
            if hist.empty:
                return json.dumps({"error": f"No historical data found for {symbol} in the last month."}, indent=2)
                
            latest_data = hist.iloc[-1]
            latest_date = latest_data.name.strftime('%Y-%m-%d')
            
            # Format 52-week data with dates
            hist_1y = stock.history(period="1y")
            if hist_1y.empty:
                 fifty_two_week_high_date = "N/A"
                 fifty_two_week_low_date = "N/A"
            else:
                fifty_two_week_high_date = hist_1y['High'].idxmax().strftime('%Y-%m-%d') if not hist_1y['High'].empty else "N/A"
                fifty_two_week_low_date = hist_1y['Low'].idxmin().strftime('%Y-%m-%d') if not hist_1y['Low'].empty else "N/A"

            # Prepare the response
            response = {
                "company_name": info.get("longName", "N/A"),
                "latest_trading_data": {
                    "date": latest_date,
                    "price": latest_data['Close'] if 'Close' in latest_data else "N/A",
                    "open_price": latest_data['Open'] if 'Open' in latest_data else "N/A",
                    "volume": latest_data['Volume'] if 'Volume' in latest_data else "N/A",
                    "change_percent": f"{((latest_data['Close'] - latest_data['Open']) / latest_data['Open'] * 100):.2f}%" if 'Close' in latest_data and 'Open' in latest_data and latest_data['Open'] != 0 else "N/A"
                },
                "52_week_high": {
                    "price": info.get("fiftyTwoWeekHigh", "N/A"),
                    "date": fifty_two_week_high_date
                },
                "52_week_low": {
                    "price": info.get("fiftyTwoWeekLow", "N/A"),
                    "date": fifty_two_week_low_date
                },
                "market_cap": info.get("marketCap", "N/A"),
                "pe_ratio": info.get("forwardPE", "N/A"), # Price-to-Earnings ratio
                "dividend_yield": info.get("dividendYield", "N/A"), # Dividend yield
                "beta": info.get("beta", "N/A"), # Beta value
                "eps": info.get("trailingEps", "N/A"), # Earnings Per Share
                "revenue_growth_yoy": info.get("revenueGrowth", "N/A"), # Year-over-year revenue growth
                "earnings_growth_yoy": info.get("earningsGrowth", "N/A"), # Year-over-year earnings growth
                "debt_to_equity": info.get("debtToEquity", "N/A"), # Debt-to-equity ratio
                "return_on_equity": info.get("returnOnEquity", "N/A"), # Return on Equity
                "business_summary": info.get("longBusinessSummary", "N/A"),
                "analyst_rating": info.get("recommendationKey", "N/A")
            }
            
            return json.dumps(response, indent=2, ensure_ascii=False) # ensure_ascii=False for Chinese characters
            
        except Exception as e:
            return json.dumps({"error": f"Error fetching data for {symbol}: {str(e)}"}, indent=2, ensure_ascii=False)

    async def _arun(self, symbol: str) -> str:
        # For async execution, you might wrap the sync call or use an async HTTP library
        # For simplicity, we'll call the sync version here, but ideally, this would be truly async
        # In a real async scenario, use libraries like aiohttp for yfinance or an async yfinance wrapper
        return self._run(symbol)
