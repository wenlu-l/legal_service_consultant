"""闲聊处理器。

处理闲聊方向（chitchat 轨道）的消息：获取当前会话历史，调用闲聊响应器生成回复。
"""
from consultant.chitchat.chitchat_responder import ChitchatResponder
from consultant.domain.messages import UserMessage, BotMessage
from consultant.domain.state import DialogueState, Turn


class ChitchatHandler:

    def __init__(self, chitchat_responder: ChitchatResponder):
        self.chitchat_responder = chitchat_responder

    async def handle(self, state: DialogueState, user_message: UserMessage) -> list[BotMessage]:
        """处理闲聊消息，返回客服回复"""
        # 1. 获取当前会话历史
        recent_turns: list[Turn] = state.shared_state.current_session().turns
        # 2. 调用闲聊响应器生成回复
        bot_message = await self.chitchat_responder.respond(recent_turns, user_message)
        return [bot_message]
