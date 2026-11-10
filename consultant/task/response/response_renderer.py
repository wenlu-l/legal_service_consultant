"""响应模板渲染器。

负责把流程中的 response / collect 步骤模板渲染成客服回复（BotMessage）：
- static 模式：直接渲染模板文本；
- rephrase 模式：先渲染基础回复，再调用 LLM 依据 prompt 润色。

同时提供 normalize_braces 把单括号 {var} 归一化为 jinja2 双括号 {{ var }}，
以兼容 system_flows.yml 中的 {history} 写法。
"""
import re

from jinja2 import Template
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from consultant.clients.llm_client import llm
from consultant.domain.flow_catalog import ResponseTemplate, ResponseMode
from consultant.domain.messages import UserMessage, BotMessage
from consultant.domain.state import DialogueState
from consultant.prompts.history_builder import HistoryBuilder

# 单括号 {var} -> 双括号 {{ var }}，不破坏已有的 {{ var }}
_SINGLE_BRACE_RE = re.compile(r"(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_.]*)\}(?!\})")


def normalize_braces(text: str | None) -> str:
    """把单括号占位符归一化为 jinja2 双括号"""
    if not text:
        return ""
    return _SINGLE_BRACE_RE.sub(r"{{ \1 }}", text)


class ResponseRenderer:

    async def respond(self, template: ResponseTemplate, state: DialogueState,
                      user_message: UserMessage) -> BotMessage:
        """渲染用户流程中的 response / collect 模板"""
        return await self.render(
            mode=template.mode,
            text=template.text,
            prompt=template.prompt,
            state=state,
            user_message=user_message,
        )

    async def render(self, mode: ResponseMode, text: str | None, prompt: str | None,
                     state: DialogueState, user_message: UserMessage,
                     context: dict | None = None) -> BotMessage:
        """通用渲染：static 直接渲染；rephrase 先渲染基础回复再调用 LLM 润色"""
        # 1. 从活跃任务获取已收集槽位，构建渲染上下文
        active_task = state.task_state.active_task
        slots = active_task.slots if active_task else {}
        render_vars = {"slots": slots, "context": context or {}}
        # 2. 渲染基础回复文本
        rendered = Template(normalize_braces(text)).render(**render_vars)

        # 3. static 模式直接返回
        if mode == ResponseMode.STATIC:
            return BotMessage(text=rendered)

        # 4. rephrase 模式：调用 LLM 润色
        prompt_tpl = PromptTemplate.from_template(normalize_braces(prompt), template_format="jinja2")
        chain = prompt_tpl | llm | StrOutputParser()
        out = await chain.ainvoke({
            "history": HistoryBuilder.build(state.shared_state.current_session().turns),
            "user_message": HistoryBuilder.render_user_message(user_message),
            "current_response": rendered,
            "slots": slots,
            "context": context or {},
        })
        return BotMessage(text=out)
