"""数据库客户端。

负责创建 SQLAlchemy 异步引擎与异步会话工厂，并在启动时自动建表。
其它模块通过 `from consultant.clients import database` 使用全局的 engine / session_factory。
"""
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession, create_async_engine

from consultant.conf.config import settings

# 模块级变量，初始值为 None，由 init_db_engine 赋值
engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db_engine():
    """项目启动时初始化引擎与会话工厂（只初始化一次）"""
    global engine, session_factory
    engine = create_async_engine(url=settings.database_url, echo=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)


async def create_tables():
    """首次启动时自动创建数据表"""
    from consultant.models.base import Base
    from consultant.models.dialogue_state_record import DialogueStateRecord  # noqa: F401 确保模型被注册
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db_engine():
    """项目关闭时释放引擎资源"""
    if engine:
        await engine.dispose()
