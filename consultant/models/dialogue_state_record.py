"""对话状态 ORM 模型。

对应 MySQL 表 dialogue_states，用于持久化每个用户的对话状态。
state_json 存放 DialogueState 对象序列化后的 JSON 字符串。
"""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from consultant.models.base import Base


class DialogueStateRecord(Base):
    __tablename__ = "dialogue_states"

    # 用户 ID，作为主键
    sender_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    # 对话状态 JSON 字符串
    state_json: Mapped[str] = mapped_column(Text, nullable=False)
