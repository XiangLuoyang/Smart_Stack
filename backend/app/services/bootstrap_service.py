"""单账户引导服务:启动时确保恰好一个模拟账户存在。"""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.account import Account

logger = logging.getLogger(__name__)

DEFAULT_ACCOUNT_NAME = "个人模拟账户"
DEFAULT_INITIAL_CASH = 1_000_000.0


def ensure_single_account(db: Session, initial_cash: float = DEFAULT_INITIAL_CASH) -> Account:
    """确保恰好一个账户存在。无账户时创建;多账户时返回第一个并警告。"""
    count = db.scalar(select(func.count(Account.id)))
    if count == 0:
        account = Account(name=DEFAULT_ACCOUNT_NAME, cash=initial_cash, status="ACTIVE")
        db.add(account)
        db.commit()
        logger.info(f"已创建默认模拟账户: {DEFAULT_ACCOUNT_NAME}, 初始资金 {initial_cash:,.0f}")
        return account
    if count > 1:
        logger.warning(f"检测到 {count} 个账户,使用第一个;建议迁移为单账户模式")
    return db.scalars(select(Account).order_by(Account.created_at).limit(1)).first()