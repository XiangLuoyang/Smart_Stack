"""pytest 共享 fixture。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 让 backend/app 和根目录 src 都能被导入
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

# 测试用临时 SQLite
os.environ["DB_PATH"] = str(PROJECT_ROOT / "data" / "test_smartstack.db")

import pytest
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from app.core.config import get_settings
from app.db.base import Base, upgrade_database


@pytest.fixture
def db_session():
    """每个测试用独立的内存 SQLite。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def migrated_engine(tmp_path, monkeypatch):
    """在临时 SQLite 文件上运行 Alembic 迁移,返回已迁移的引擎。"""
    url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    monkeypatch.setenv("DB_URL", url)
    get_settings.cache_clear()
    upgrade_database(url)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    try:
        yield engine
    finally:
        engine.dispose()
        get_settings.cache_clear()