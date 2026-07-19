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

from app.db.base import Base


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
