"""应用配置:从环境变量 + .env 读取,集中管理。

把原来散落在 src/config/settings.py 里的全局单例收敛到这里,
通过依赖注入(get_settings())访问,避免模块级实例化带来的测试困难。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


class FeesConfig(BaseSettings):
    """A 股交易成本模型,默认值按主流券商费率。"""

    model_config = SettingsConfigDict(env_prefix="FEES_", env_file=".env", extra="ignore")

    commission_rate: float = Field(0.00025, description="佣金费率(双边)")
    commission_min: float = Field(5.0, description="佣金最低收取金额(元)")
    stamp_duty_rate: float = Field(0.001, description="印花税率(仅卖出)")
    transfer_fee_rate: float = Field(0.00002, description="过户费率(沪市双边)")


class MarketConfig(BaseSettings):
    """行情调度配置。"""

    model_config = SettingsConfigDict(env_prefix="MARKET_", env_file=".env", extra="ignore")

    quote_poll_seconds: int = 60
    limit_order_match_seconds: int = 15
    stop_loss_scan_seconds: int = 30
    snapshot_retention_days: int = 30

    # 每日研究管线调度(Asia/Shanghai 时区)
    daily_research_hour: int = 16
    daily_research_minute: int = 30
    settlement_hour: int = 17
    settlement_minute: int = 0


class Settings(BaseSettings):
    """全局配置入口。"""

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Smart Stack 操盘工作台"
    debug: bool = False

    # 数据库
    db_path: Path = Field(default=DATA_DIR / "smartstack.db")
    db_url: Optional[str] = None  # 优先于 db_path

    # CORS
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
        ]
    )

    # LLM(沿用旧 env 变量名,与 src/llm_analysis 保持兼容)
    llm_model_name: str = "deepseek/deepseek-chat"
    llm_api_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: Optional[str] = None
    llm_temperature: float = 0.3

    # 子配置
    fees: FeesConfig = Field(default_factory=FeesConfig)
    market: MarketConfig = Field(default_factory=MarketConfig)

    @property
    def sqlalchemy_url(self) -> str:
        if self.db_url:
            return self.db_url
        # 确保父目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{self.db_path.as_posix()}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """全局单例,通过依赖注入使用。"""
    return Settings()
