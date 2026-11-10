"""澄清响应器。

当轮次计划校验失败时，根据失败原因（ClarifyReason）先生成基础澄清提示，
再调用 LLM 改写为更自然的客服回复。
"""
import json
from dataclasses import asdict

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from consultant.clients.llm_client import llm
from consultant.domain.messages import UserMessage, BotMessage
from consultant.domain.plan import ClarifyReason
from consultant.domain.state import DialogueState
from consultant.prompts.history_builder import HistoryBuilder
from consultant.prompts.prompt_loader import load_prompt


class ClarifyResponder:

    async def respond(self, reason: ClarifyReason, state: DialogueState,
                      user_message: UserMessage) -> list[BotMessage]:
        """根据澄清原因生成澄清回复"""
        # 1. 基于原因生成基础澄清提示
        clarify_message = self._build_clarify_message(reason, state)

        # 2. 调用 LLM 改写基础提示
        prompt = PromptTemplate.from_template(load_prompt("clarify_respond"), template_format="jinja2")
        chain = prompt | llm | StrOutputParser()
        text = await chain.ainvoke({
            "reason": reason.value,
            "clarify_message": clarify_message,
            "focused_object": json.dumps(asdict(state.shared_state.focused_object), ensure_ascii=False)
            if state.shared_state.focused_object else None,
            "history": HistoryBuilder.build(state.shared_state.current_session().turns),
            "user_message": HistoryBuilder.render_user_message(user_message),
        })
        return [BotMessage(text=text)]

    def _build_clarify_message(self, reason: ClarifyReason, state: DialogueState) -> str:
        """根据澄清原因生成基础提示文本"""
        if reason is ClarifyReason.MISSING_TRACK:
            return "你是想先办理业务，还是先咨询课程信息呢？"
        if reason is ClarifyReason.MULTIPLE_TRACKS:
            return "你这次同时提到了多个方向。我们先处理一个，你想先办业务还是先咨询课程信息呢？"
        if reason is ClarifyReason.MISSING_TASK_COMMANDS:
            return "你这次是想办理什么业务呢？比如课程咨询、订单查询、学习进度、退款或提交工单。"
        if reason is ClarifyReason.MISSING_KNOWLEDGE_INTENT:
            return "你是想了解课程信息、退费政策，还是报名考试政策呢？"
        if reason is ClarifyReason.MISSING_FOCUSED_OBJECT:
            return "请先发送你想咨询的对象（课程或订单），我再继续帮你看。"
        if reason is ClarifyReason.OBJECT_REQUIRES_INTENT:
            focused_object = state.shared_state.focused_object
            if focused_object is not None and focused_object.type == "order":
                return "我已经收到这个订单了。你想查订单状态、学习进度，还是申请退款呢？"
            if focused_object is not None and focused_object.type == "course":
                return "我已经收到这个课程了。你想了解课程内容、班次安排，还是价格呢？"
        if reason is ClarifyReason.INVALID_TASK_COMMAND:
            return "当前任务状态不支持这个操作，请告诉我你想开始、继续还是取消哪个任务。"
        if reason is ClarifyReason.UNKNOWN_KNOWLEDGE_INTENT:
            return "我暂时无法识别这个咨询方向，你可以具体说说想了解的课程、订单或退费问题。"
        return "我还需要再确认一下你的意思，你可以换个更具体的说法告诉我。"
