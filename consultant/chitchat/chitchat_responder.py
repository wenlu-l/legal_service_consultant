"""闲聊响应器。

结合历史对话 + 本轮用户消息，调用 LLM 生成一句自然闲聊回复。
"""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from consultant.clients.llm_client import llm
from consultant.domain.messages import UserMessage, BotMessage
from consultant.domain.state import Turn
from consultant.prompts.history_builder import HistoryBuilder
from consultant.prompts.prompt_loader import load_prompt


class ChitchatResponder:

    async def respond(self, recent_turns: list[Turn], user_message: UserMessage) -> BotMessage:
        """结合历史与用户消息生成闲聊回复"""
        # 1. 加载提示词
        prompt = PromptTemplate.from_template(load_prompt("chitchat_respond"), template_format="jinja2")
        # 2. 构建 chain
        chain = prompt | llm | StrOutputParser()
        # 3. 调用 LLM 生成回复
        text = await chain.ainvoke({
            "history": HistoryBuilder.build(recent_turns),
            "user_message": HistoryBuilder.render_user_message(user_message),
        })
        # 4. 封装结果
        return BotMessage(text=text)
