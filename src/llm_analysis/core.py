import os
from dotenv import load_dotenv
from crewai import Agent, Crew, Process, Task
from crewai.llm import LLM  # Corrected import for LLM
from pydantic import BaseModel
from src.tools.financial_tools import YFinanceStockTool

# Load environment variables from .env file
load_dotenv()

# Define Pydantic models for structured output (can be expanded as needed)
class StockAnalysisReport(BaseModel):
    symbol: str
    report_markdown: str
    # Add other structured fields if the LLM is expected to return them directly

# Initialize LLM based on environment variables
def get_llm():
    """Initializes and returns the LLM based on environment variables."""

    # 强制重新加载.env文件，确保使用最新配置
    load_dotenv(override=True)

    model_name = os.getenv("LLM_MODEL_NAME", "deepseek-chat") # 正确的默认值
    api_base_url = os.getenv("LLM_API_BASE_URL", "https://api.deepseek.com") # 正确的默认值
    api_key = os.getenv("LLM_API_KEY") # API Key is mandatory

    if not api_key:
        raise ValueError("LLM_API_KEY not found in environment variables. Please set it in your .env file.")
    if not model_name: # Should have a default, but good practice to check if user clears it
        raise ValueError("LLM_MODEL_NAME not found in environment variables or code defaults. Please set it.")
    if not api_base_url:
        raise ValueError("LLM_API_BASE_URL not found in environment variables or code defaults. Please set it.")

    # Default temperature and system prompt, can also be moved to .env if needed
    temperature = float(os.getenv("LLM_TEMPERATURE", 0.3))
    system_prompt_text = os.getenv("LLM_SYSTEM_PROMPT", "你是一个专业的中文金融分析师。请始终使用中文回答所有问题，保持专业性的同时确保语言表达清晰易懂。对于专业术语，在首次出现时提供中文解释。")

    print(f"Initializing LLM with: Model={model_name}, BaseURL={api_base_url}, Temp={temperature}") # For debugging

    return LLM(
        model=model_name,
        api_base=api_base_url,
        api_key=api_key,
        temperature=temperature,
        # timeout=120, # Optional: set a timeout for API calls
        # NOTE: Do NOT pass system_prompt here — crewai 1.14.3 leaks unknown
        # kwargs into additional_params which are forwarded to the OpenAI API,
        # causing: "Completions.create() got an unexpected keyword argument 'system_prompt'"
    )

# Create agents and tasks for financial analysis
def create_financial_analysis_crew(symbol: str):
    """
    Creates and configures the crew for financial analysis of a given stock symbol.
    Returns the Crew object.
    """
    llm = get_llm()
    
    # Initialize the custom stock tool
    stock_tool = YFinanceStockTool()
    
    # Define Stock Analysis Agent
    stock_analysis_agent = Agent(
        role="华尔街资深金融分析师",
        goal=f"对 {symbol} 股票进行全面的、数据驱动的分析，利用实时市场数据。",
        backstory="""你是一位拥有超过15年股票研究经验的资深华尔街分析师。
                     你以细致入微的分析和数据驱动的洞察力而闻名。
                     你始终基于实时市场数据进行分析，绝不依赖过时的信息或预先存在的知识。
                     你擅长解读复杂的金融指标、市场趋势，并提供可操作的投资见解。
                     请确保你的分析全面且深入。""",
        llm=llm,
        tools=[stock_tool],
        verbose=True, # Set to False in production if too noisy
        # memory=True,  # Removed for compatibility with older crewai versions like 0.119.0
        allow_delegation=False # Depending on complexity, you might allow delegation
    )

    # Define Report Writing Agent
    report_writer_agent = Agent(
        role="专业金融报告撰写专家",
        goal=f"将 {symbol} 股票的详细金融分析转化为一份专业、全面且易于理解的投资报告。",
        backstory="""你是一位专业的金融撰稿人，拥有撰写机构级研究报告的丰富经验。
                     你擅长以清晰、结构化的方式呈现复杂的金融数据和分析结果。
                     你始终遵循最高的专业标准，同时确保报告对各类投资者都易于理解并具有可操作性。
                     你以清晰的数据可视化、精准的趋势分析和中肯的风险评估能力而著称。""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

    # Define Analysis Task
    analysis_task = Task(
        description=f"""请对 {symbol} 股票进行深入且全面的中文分析。务必使用 stock_data_tool 工具获取最新的实时数据。
        你的分析必须覆盖以下所有方面，并确保数据的准确性和时效性：

        1.  **最新交易信息 (最高优先级)**:
            *   最新股票价格及其具体日期和时间。
            *   当日涨跌幅（金额和百分比）。
            *   最新交易量。
            *   当前市场状态（例如：开市、收市、盘前、盘后）。
            *   明确标注数据是否来自最近的交易时段。

        2.  **52周价格表现 (关键指标)**:
            *   52周最高价及其具体发生日期。
            *   52周最低价及其具体发生日期。
            *   当前价格在52周价格区间内所处的位置（例如，百分位数）。
            *   计算当前价格距离52周高点和低点的百分比。

        3.  **核心财务指标深度分析**:
            *   公司市值 (Market Cap)。
            *   市盈率 (P/E Ratio) - 动态市盈率和静态市盈率（如果可获取）。
            *   市净率 (P/B Ratio)。
            *   每股收益 (EPS)。
            *   股息收益率 (Dividend Yield)（如适用）。
            *   收入增长率 (Revenue Growth YoY)。
            *   利润增长率 (Earnings Growth YoY)。
            *   资产负债率 (Debt-to-Equity Ratio)。
            *   股本回报率 (Return on Equity - ROE)。

        4.  **技术分析洞察**:
            *   近期价格走势图解读（例如，过去1个月、3个月）。
            *   成交量变化分析及其与价格变动的关系。
            *   关键技术指标解读（例如，移动平均线MA, 相对强弱指数RSI, MACD）。（如果工具直接提供这些，请解读；如果工具不提供，说明无法获取）

        5.  **公司与市场背景**:
            *   公司业务概要和主要产品/服务。
            *   行业地位和主要竞争对手。
            *   分析师评级摘要 (Analyst Rating/Recommendation)。
            *   识别并列出与该公司相关的主要潜在风险因素。

        **重要指令**:
        *   分析的起点必须是使用 stock_data_tool 获取实时数据。
        *   报告的开头部分应立即呈现最新的股票价格和52周关键数据。
        *   所有提及的价格点、财务数据点都必须包含具体的日期或数据周期。
        *   清晰标注每个关键数据点的信息来源时间。
        *   进行必要的百分比变化计算，并清晰展示。
        *   使用获取到的实时数据验证所有数字和结论。
        *   在可能的情况下，将当前指标与公司的历史趋势和行业平均水平进行比较。
        *   所有内容必须使用简体中文。""",
        expected_output=f"一份关于 {symbol} 股票的综合中文分析报告，详细涵盖所有指定分析点，信息准确，数据实时，并清晰分段。",
        agent=stock_analysis_agent
    )

    # Define Report Generation Task
    report_task = Task(
        description=f"""请基于 {stock_analysis_agent.role} 对 {symbol} 股票的分析结果，撰写一份专业、详尽且易于理解的中文投资报告。
        该报告必须严格遵循以下结构和内容要求：

        1.  **报告结构**:
            *   **执行摘要 (Executive Summary)**: 简明扼要地总结核心分析发现、主要结论和投资建议。
            *   **市场地位与公司概况**: 介绍公司业务、行业地位、竞争优势等。
            *   **财务指标深度分析**: 详细呈现并解读关键财务数据和比率。
            *   **技术分析解读**: 分析股价走势、成交量和技术指标。
            *   **风险评估**: 明确指出投资该股票的主要潜在风险。
            *   **投资展望与建议**: 基于整体分析，给出对未来的展望和具体的投资建议（例如：买入、持有、卖出，并说明理由）。
            *   **免责声明**: 加入标准的投资风险免责声明。

        2.  **内容要求**:
            *   所有引用的数据点（价格、财务指标等）必须包含其对应的时间戳或数据周期。
            *   使用表格形式清晰呈现关键财务指标和技术指标的对比。
            *   使用项目符号（bullet points）列出关键的分析见解、优势、劣势和机会。
            *   在适当的地方，将公司的财务指标与行业平均水平或主要竞争对手进行比较。
            *   对报告中出现的专业金融术语，在首次出现时提供简洁明了的中文解释。
            *   突出强调潜在的投资风险和不确定性。

        3.  **格式化要求**:
            *   报告全文必须使用 Markdown 格式。
            *   合理使用标题（H1, H2, H3）来组织章节，确保逻辑清晰。
            *   使用 Markdown 表格来展示数据。
            *   适当使用粗体 (**bold**) 来强调关键指标、术语或结论。
            *   使用项目符号 (* or -) 来列举要点。
            *   考虑使用趋势指示表情符号（如 📈 表示增长, 📉 表示下降, ⚠️ 表示风险）来增强可读性，但需专业且不滥用。

        **重要指令**:
        *   保持绝对专业的语气和客观的分析立场。
        *   清晰地说明所有关键数据和信息的来源（主要应来自 stock_data_tool 的输出）。
        *   确保报告内容完整、逻辑连贯、易于非专业人士理解。
        *   最终输出必须是一份可以直接使用的 Markdown 格式的完整报告文本。
        *   所有内容必须使用简体中文。""",
        expected_output=f"一份关于 {symbol} 股票的专业中文投资报告，采用 Markdown 格式，包含所有要求的章节、数据表格、分析见解和视觉指标。报告应结构清晰、内容详实、语言专业。",
        agent=report_writer_agent,
        # context=[analysis_task] # Ensure report task uses the output of analysis_task
    )

    # Assemble the crew
    financial_crew = Crew(
        agents=[stock_analysis_agent, report_writer_agent],
        tasks=[analysis_task, report_task],
        process=Process.sequential,  # Tasks will be executed one after another
        verbose=True # True for detailed logs, False for no logs. (Changed from 2)
        # memory=True # Optional: enable memory for the entire crew for longer conversations
        # manager_llm=get_llm() # Optional: assign a manager LLM for complex crew coordination
    )

    return financial_crew

# Example usage (for testing this module directly)
if __name__ == '__main__':
    # This part will only run when the script is executed directly
    # For actual use, you'll import and call create_financial_analysis_crew from another script
    
    # Ensure DEEPSEEK_API_KEY is set in your .env file in the project root
    # Example: DEEPSEEK_API_KEY="your_actual_api_key"
    
    sample_symbol = "AAPL" # Example stock symbol
    print(f"Attempting to create and run financial analysis crew for {sample_symbol}...")
    
    try:
        crew_instance = create_financial_analysis_crew(sample_symbol)
        print(f"Crew created for {sample_symbol}. Kicking off analysis...")
        # Note: kickoff() can take some time depending on the LLM and tasks
        result = crew_instance.kickoff()
        
        print(f"\n--- Analysis Report for {sample_symbol} ---")
        print(result) # The result here is the raw output from the last task
        
        # If you defined StockAnalysisReport and expect structured output from the crew:
        # report_data = StockAnalysisReport(symbol=sample_symbol, report_markdown=result)
        # print("\n--- Structured Report ---")
        # print(report_data.model_dump_json(indent=2))

    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except Exception as e:
        print(f"An error occurred during the crew execution: {e}")
        import traceback
        traceback.print_exc()
