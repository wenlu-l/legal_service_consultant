"""路由层入参与出参模型（pydantic）。"""
from dataclasses import field

from pydantic import BaseModel


class ChatObject(BaseModel):
    """卡片对象（课程/订单）"""
    type: str  # 卡片类型：course、order
    id: str  # 卡片 ID
    title: str | None = None  # 标题
    attributes: dict = field(default_factory=dict)  # 附加属性


class ChatRequest(BaseModel):
    """聊天入参"""
    sender_id: str  # 用户 ID，必填
    message_id: str | None = None  # 消息 ID
    text: str | None = None  # 文本内容
    object: ChatObject | None = None  # 卡片对象


class ChatBotMessage(BaseModel):
    """单条客服回复，可以是文本或对象"""
    text: str | None = None
    object: ChatObject | None = None


class ChatResponse(BaseModel):
    """客服响应，可包含多条回复"""
    sender_id: str
    message_id: str
    messages: list[ChatBotMessage]


class HistoryMessage(BaseModel):
    """用户或客服单条历史消息"""
    role: str  # user 用户 / bot 客服
    text: str | None = None
    object: ChatObject | None = None


class HistoryResponse(BaseModel):
    """历史消息响应"""
    sender_id: str
    messages: list[HistoryMessage]
