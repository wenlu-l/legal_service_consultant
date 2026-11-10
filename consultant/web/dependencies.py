"""FastAPI 依赖项。

提供路由所需的依赖注入：数据库会话、对话状态仓库、对话引擎、对话服务。
对话引擎通过全局变量只初始化一次（init_dialogue_engine 在启动时调用）。
"""
from typing import Annotated, AsyncGenerator

from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from consultant.clients import database
from consultant.engine.builder import build_engine
from consultant.engine.dialogue_engine import DialogueEngine
from consultant.repository.dialogue_state_record_repository import DialogueStateRecordRepository
from consultant.service.dialogue_service import DialogueService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（前提：init_db_engine 已调用）"""
    async with database.session_factory() as session:
        yield session


async def get_dialogue_state_repository(
    session: Annotated[AsyncSession, Depends(get_session)]
) -> DialogueStateRecordRepository:
    """获取对话状态仓库"""
    return DialogueStateRecordRepository(session)


# 全局对话引擎，只初始化一次
_dialogue_engine: DialogueEngine | None = None


def init_dialogue_engine():
    """项目启动时调用一次，构建对话引擎"""
    global _dialogue_engine
    _dialogue_engine = build_engine()


async def get_dialogue_engine() -> DialogueEngine:
    """获取对话引擎"""
    return _dialogue_engine


async def get_dialogue_service(
    dialogue_state_repository: Annotated[DialogueStateRecordRepository, Depends(get_dialogue_state_repository)],
    dialogue_engine: Annotated[DialogueEngine, Depends(get_dialogue_engine)],
) -> DialogueService:
    """获取对话服务"""
    return DialogueService(
        dialogue_state_repository=dialogue_state_repository,
        dialogue_engine=dialogue_engine,
    )
