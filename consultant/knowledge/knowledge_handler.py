"""知识检索处理器。

处理知识方向（knowledge 轨道）的消息：根据意图列表确定需要访问的信息提供者，
并发检索知识片段，最后调用响应器生成客服回复。
"""
import asyncio

from loguru import logger

from consultant.domain.knowledge import KnowledgeIntent, KnowledgeChunk
from consultant.domain.messages import UserMessage, BotMessage
from consultant.domain.state import DialogueState
from consultant.knowledge.providers import KnowledgeProvider
from consultant.knowledge.responder import KnowledgeResponder


class KnowledgeHandler:

    def __init__(self, knowledge_intents: dict[str, KnowledgeIntent],
                 providers: list[KnowledgeProvider], knowledge_responder: KnowledgeResponder):
        self.knowledge_intents = knowledge_intents  # 系统支持的知识意图
        self.providers_by_id: dict[str, KnowledgeProvider] = {p.provider_id: p for p in providers}
        self.knowledge_responder = knowledge_responder

    async def handle(self, intents: list[str], state: DialogueState,
                     user_message: UserMessage) -> list[BotMessage]:
        """接收意图列表，检索知识并生成客服回复"""
        # 1. 意图 ID 列表转为知识意图配置列表
        knowledge_intents = [self.knowledge_intents.get(intent) for intent in intents]

        # 2. 收集所有意图关联的 provider_id 并去重
        all_provider_ids: set[str] = set()
        for intent in knowledge_intents:
            all_provider_ids.update(intent.provider_ids)

        # 3. 并发调用各 provider 检索知识片段（忽略未注册的 provider_id，避免崩溃）
        async def _retrieve(provider_id: str) -> list[KnowledgeChunk]:
            provider = self.providers_by_id.get(provider_id)
            if provider is None:
                logger.warning("知识提供者未注册：{}", provider_id)
                return []
            return await provider.retrieve(state, user_message)

        chunks_list = await asyncio.gather(*[_retrieve(pid) for pid in all_provider_ids])
        chunks: list[KnowledgeChunk] = [chunk for chunks in chunks_list for chunk in chunks]

        # 4. 调用响应器生成客服回复
        bot_message = await self.knowledge_responder.respond(
            state.shared_state.current_session().turns, user_message, chunks
        )
        return [bot_message]
