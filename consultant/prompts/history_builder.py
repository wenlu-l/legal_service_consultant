"""对话历史构建器。

把会话中的多轮对话（Turn 列表）格式化为 LLM 提示词中的对话历史文本，例如：
    USER: 你好
    BOT: 你好，我是法硕研途智能客服
"""
import json
from dataclasses import asdict

from consultant.domain.messages import UserMessage, MessageType, BotMessage
from consultant.domain.state import Turn


class HistoryBuilder:

    @classmethod
    def render_user_message(cls, user_message: UserMessage) -> str:
        """渲染单条用户消息"""
        if user_message.type == MessageType.TEXT:
            return f"USER: {user_message.text.strip()}"
        # 卡片对象消息转为 JSON 字符串
        return f"USER: {json.dumps(asdict(user_message.object), ensure_ascii=False)}"

    @classmethod
    def render_bot_message(cls, bot_message: BotMessage) -> str:
        """渲染单条客服回复"""
        if bot_message.text:
            return f"BOT: {bot_message.text.strip()}"
        return f"BOT: {json.dumps(asdict(bot_message.object), ensure_ascii=False)}"

    @classmethod
    def build(cls, turns: list[Turn]) -> str:
        """把多轮对话拼接为历史文本，先用户消息、再客服回复"""
        messages: list[str] = []
        for turn in turns:
            messages.append(cls.render_user_message(turn.user_message))
            for bot_message in turn.bot_messages:
                messages.append(cls.render_bot_message(bot_message))
        return "\n".join(messages)
