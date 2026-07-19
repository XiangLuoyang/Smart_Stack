"""SQLAlchemy 声明基类 + 会话工厂。

遵循 plan 决策:不引入 Alembic,用 Base.metadata.create_all 建表;
schema 变更靠删除重建(纸面账户数据可丢弃)。
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


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


def init_db() -> None:
    """创建所有表。应在应用启动时调用一次。"""
    # 触发所有模型导入,确保 metadata 已注册
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入用的会话生成器。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
