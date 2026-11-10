"""对话 Service 层所需的数据类。

定义三类消息模型：
- MessageObject：卡片对象（课程 / 订单），用于前端点击卡片发送的富消息；
- UserMessage / BotMessage：业务层处理时的用户消息与客服回复；
- ProcessResult：引擎处理完一轮消息后返回的结果，对应接口层的 ChatResponse。
"""
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class MessageObject:
    """业务层卡片对象"""
    type: str  # 卡片类型：course 课程 / order 订单
    id: str  # 卡片 ID（课程 ID 或订单号）
    title: str | None = None  # 卡片标题
    attributes: dict = field(default_factory=dict)  # 卡片附加属性


class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"  # 文本消息
    OBJECT = "object"  # 卡片对象消息


@dataclass
class UserMessage:
    """用于业务处理的用户消息"""
    sender_id: str  # 用户 ID
    message_id: str  # 本轮消息 ID
    type: MessageType  # 消息类型（文本 / 卡片对象）
    text: str | None = None  # 文本内容
    object: MessageObject | None = None  # 卡片对象内容


@dataclass
class BotMessage:
    """客服回复消息"""
    text: str | None = None  # 文本回复
    object: MessageObject | None = None  # 卡片回复


@dataclass
class ProcessResult:
    """引擎处理本轮消息后的回复结果"""
    sender_id: str  # 用户 ID
    message_id: str  # 本轮消息 ID
    messages: list[BotMessage]  # 客服回复列表
