import json
import logging
from contextlib import contextmanager
from typing import Any, Optional

from world_seek.internal.wrappers import register_connection
from world_seek.env import (
    WORLD_SEEK_DIR,
    DATABASE_URL,
    DATABASE_SCHEMA,
    SRC_LOG_LEVELS,
    DATABASE_POOL_MAX_OVERFLOW,
    DATABASE_POOL_RECYCLE,
    DATABASE_POOL_SIZE,
    DATABASE_POOL_TIMEOUT,
)
from peewee_migrate import Router
from sqlalchemy import Dialect, create_engine, MetaData, types
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.sql.type_api import _T
from typing_extensions import Self

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])


class JSONField(types.TypeDecorator):
    impl = types.Text
    cache_ok = True

    def process_bind_param(self, value: Optional[_T], dialect: Dialect) -> Any:
        return json.dumps(value)

    def process_result_value(self, value: Optional[_T], dialect: Dialect) -> Any:
        try:
            # 如果值是None，直接返回空字典
            if value is None:
                return {}
                
            # 如果已经是字典，直接返回
            if isinstance(value, dict):
                return value
                
            # 如果是空字符串，返回空字典
            if isinstance(value, str) and not value.strip():
                return {}
                
            # 尝试解析JSON字符串
            if isinstance(value, str):
                return json.loads(value)
                
            # 其他情况返回空字典
            return {}
            
        except Exception as e:
            log.error(f"JSON解析错误: {str(e)}, 值: {value}")
            return {}

    def copy(self, **kw: Any) -> Self:
        return JSONField(self.impl.length)

    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is not None:
            return json.loads(value)


# Workaround to handle the peewee migration
# This is required to ensure the peewee migration is handled before the alembic migration
def handle_peewee_migration(DATABASE_URL):
    # db = None
    try:
        # Replace the postgresql:// with postgres:// to handle the peewee migration
        db = register_connection(DATABASE_URL.replace("postgresql://", "postgres://"))
        migrate_dir = WORLD_SEEK_DIR / "internal" / "migrations"
        router = Router(db, logger=log, migrate_dir=migrate_dir)
        router.run()
        db.close()

    except Exception as e:
        log.error(f"Failed to initialize the database connection: {e}")
        raise
    finally:
        # Properly closing the database connection
        if db and not db.is_closed():
            db.close()

        # Assert if db connection has been closed
        assert db.is_closed(), "Database connection is still open."


handle_peewee_migration(DATABASE_URL)


SQLALCHEMY_DATABASE_URL = DATABASE_URL
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    if DATABASE_POOL_SIZE > 0:
        # 使用配置的连接池设置
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            pool_size=DATABASE_POOL_SIZE,
            max_overflow=DATABASE_POOL_MAX_OVERFLOW,
            pool_timeout=DATABASE_POOL_TIMEOUT,
            pool_recycle=DATABASE_POOL_RECYCLE,
            pool_pre_ping=True,
            poolclass=QueuePool,
            # 添加连接池事件监听
            echo_pool=True,  # 启用连接池日志
        )
    else:
        # 使用优化的默认连接池设置而不是NullPool
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            pool_size=10,  # 默认连接池大小
            max_overflow=5,  # 默认溢出连接
            pool_timeout=20,  # 默认超时时间
            pool_recycle=1800,  # 默认连接回收时间(30分钟)
            pool_pre_ping=True,
            poolclass=QueuePool,
            echo_pool=True,  # 启用连接池日志
        )

# 添加连接池监控事件
from sqlalchemy import event
from sqlalchemy.pool import Pool

@event.listens_for(Pool, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """为新连接设置优化参数"""
    if 'sqlite' not in SQLALCHEMY_DATABASE_URL:
        # 对于PostgreSQL连接，设置一些优化参数
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("SET statement_timeout = '300s'")  # 5分钟查询超时
            cursor.execute("SET idle_in_transaction_session_timeout = '60s'")  # 1分钟事务空闲超时
            cursor.close()
        except Exception as e:
            log.warning(f"设置数据库连接参数失败: {e}")

@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """连接被检出时的事件"""
    log.debug("数据库连接被检出")

@event.listens_for(Pool, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """连接被归还时的事件"""
    log.debug("数据库连接被归还")


SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)
metadata_obj = MetaData(schema=DATABASE_SCHEMA)
Base = declarative_base(metadata=metadata_obj)
Session = scoped_session(SessionLocal)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


get_db = contextmanager(get_session)
