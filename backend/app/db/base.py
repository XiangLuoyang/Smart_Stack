"""SQLAlchemy 声明基类 + 会话工厂 + Alembic 迁移入口。

schema 变更通过 Alembic 版本化迁移管理(见 backend/migrations);
init_db() 在应用启动时执行 `alembic upgrade head` 建表/升级。
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import BACKEND_ROOT, get_settings


class Base(DeclarativeBase):
    """所有 ORM 模型的声明基类。"""


def _build_engine():
    settings = get_settings()
    # check_same_thread=False:FastAPI 多线程场景(后台调度器 + 请求线程)共用引擎
    return create_engine(
        settings.sqlalchemy_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        future=True,
    )


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def upgrade_database(url: str | None = None) -> None:
    """运行 Alembic 迁移到最新版本。

    url 为空时使用应用设置中的数据库地址。
    """
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    if url:
        cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def init_db() -> None:
    """通过 Alembic 迁移建表/升级。应在应用启动时调用一次。"""
    # 触发所有模型导入,确保 metadata 已注册(供迁移与校验使用)
    from app import models  # noqa: F401

    upgrade_database()


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入用的会话生成器。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()