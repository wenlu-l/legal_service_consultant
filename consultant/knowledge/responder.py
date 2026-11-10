"""知识检索响应器。

基于检索到的知识片段 + 对话历史 + 用户消息，调用 LLM 生成一条客服回复。
"""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from consultant.clients.llm_client import llm
from consultant.domain.knowledge import KnowledgeChunk
from consultant.domain.messages import UserMessage, BotMessage
from consultant.domain.state import Turn
from consultant.prompts.history_builder import HistoryBuilder
from consultant.prompts.prompt_loader import load_prompt


class KnowledgeResponder:

    async def respond(self, turns: list[Turn], user_message: UserMessage,
                      chunks: list[KnowledgeChunk]) -> BotMessage:
        """基于知识片段生成客服回复"""
        prompt = PromptTemplate.from_template(load_prompt("knowledge_respond"), template_format="jinja2")
        chain = prompt | llm | StrOutputParser()
        # 1. 拼接检索到的知识片段
        knowledge_content = "\n\n".join([chunk.content for chunk in chunks])
        # 2. 调用 LLM 生成回复
        result = await chain.ainvoke({
            "history": HistoryBuilder.build(turns),
            "user_message": HistoryBuilder.render_user_message(user_message),
            "knowledge_content": knowledge_content,
        })
        return BotMessage(text=result)
