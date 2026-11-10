"""聊天路由。

对外提供两个接口：
- POST /api/chat：处理一轮对话，返回客服回复；
- GET /api/chat/history：查询用户历史对话。
"""
import uuid
from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends
from loguru import logger

from consultant.domain.messages import UserMessage, MessageType, MessageObject, ProcessResult
from consultant.domain.state import DialogueState
from consultant.service.dialogue_service import DialogueService
from consultant.web.dependencies import get_dialogue_service
from consultant.web.schemas import ChatRequest, ChatResponse, ChatBotMessage, HistoryResponse, HistoryMessage, ChatObject

chat_router = APIRouter(tags=["智能客服"])


def _build_user_message(chat_request: ChatRequest) -> UserMessage:
    """将接口模型转为业务模型"""
    return UserMessage(
        sender_id=chat_request.sender_id,
        message_id=chat_request.message_id if chat_request.message_id else str(uuid.uuid4()),
        text=chat_request.text,
        type=MessageType.TEXT if chat_request.text else MessageType.OBJECT,
        object=MessageObject(
            id=chat_request.object.id,
            type=chat_request.object.type,
            title=chat_request.object.title,
            attributes=chat_request.object.attributes,
        ) if chat_request.object else None,
    )


def _build_chat_object(message_object: MessageObject) -> ChatObject:
    """将业务层卡片对象转为接口模型"""
    return ChatObject(
        type=message_object.type,
        id=message_object.id,
        title=message_object.title,
        attributes=message_object.attributes,
    )


def _build_chat_response(process_result: ProcessResult) -> ChatResponse:
    """将业务层结果转为接口响应"""
    return ChatResponse(
        sender_id=process_result.sender_id,
        message_id=process_result.message_id,
        messages=[ChatBotMessage(
            text=bot_message.text,
            object=_build_chat_object(bot_message.object) if bot_message.object else None,
        ) for bot_message in process_result.messages] if process_result.messages else [],
    )


@chat_router.post("/api/chat")
async def chat(chat_request: ChatRequest,
               dialogue_service: Annotated[DialogueService, Depends(get_dialogue_service)]) -> ChatResponse:
    """处理一轮对话"""
    # 1. 接口模型转为业务模型
    user_message = _build_user_message(chat_request)
    # 2. 调用业务层处理消息
    process_result = await dialogue_service.process_message(user_message)
    logger.info("本轮消息回复：{}", process_result)
    # 3. 业务层结果转为接口响应
    return _build_chat_response(process_result)


@chat_router.get("/api/chat/history")
async def chat_history(sender_id: str,
                       dialogue_service: Annotated[DialogueService, Depends(get_dialogue_service)]) -> HistoryResponse:
    """查询历史对话"""
    # 1. 根据用户 ID 查询对话状态
    state: DialogueState = await dialogue_service.get_state(sender_id)
    # 2. 遍历会话与轮次，收集用户消息与客服回复
    history_messages: list[HistoryMessage] = []
    for session in state.shared_state.sessions:
        for turn in session.turns:
            history_messages.append(HistoryMessage(
                role="user",
                text=turn.user_message.text,
                object=_build_chat_object(turn.user_message.object) if turn.user_message.object else None,
            ))
            history_messages.extend([HistoryMessage(
                role="bot",
                text=bot_message.text,
                object=_build_chat_object(bot_message.object) if bot_message.object else None,
            ) for bot_message in turn.bot_messages])
    # 3. 封装历史响应
    return HistoryResponse(sender_id=sender_id, messages=history_messages)
