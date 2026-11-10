"""轮次规划器。

基于对话状态 + 用户消息 + 系统支持的流程清单与知识意图，调用 LLM 生成本轮计划
（TurnPlan）。计划包含三个方向：task（任务办理）、knowledge（知识检索）、chitchat（闲聊）。
"""
import json
from dataclasses import asdict

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from loguru import logger

from consultant.clients.llm_client import llm
from consultant.domain.flow_catalog import FlowCatalog
from consultant.domain.knowledge import KnowledgeIntent
from consultant.domain.messages import UserMessage
from consultant.domain.plan import TurnPlan
from consultant.domain.state import DialogueState
from consultant.prompts.history_builder import HistoryBuilder
from consultant.prompts.prompt_loader import load_prompt


class TurnPlanner:

    async def predict(self, state: DialogueState, user_message: UserMessage, flow_catalog: FlowCatalog,
                      knowledge_intents: dict[str, KnowledgeIntent]) -> TurnPlan:
        """调用 LLM 生成本轮计划"""
        # 1. 准备提示词上下文变量（共 6 个）
        # 1.1 对话历史
        conversation_history = HistoryBuilder.build(state.shared_state.current_session().turns)
        # 1.2 用户消息
        rendered_user_message = HistoryBuilder.render_user_message(user_message)
        # 1.3 焦点对象
        focused_object_json = (
            json.dumps(asdict(state.shared_state.focused_object), ensure_ascii=False, indent=2)
            if state.shared_state.focused_object else None
        )
        # 1.4 任务状态（活跃任务 + 暂停任务）
        task_state_json = json.dumps(asdict(state.task_state), ensure_ascii=False, indent=2)
        # 1.5 系统支持的知识意图
        knowledge_intents_dict = [{ki.id: ki.description} for ki in knowledge_intents.values()]
        knowledge_intents_json = json.dumps(knowledge_intents_dict, ensure_ascii=False, indent=2)
        # 1.6 系统支持的流程清单（过滤掉 steps 明细）
        flows_dict = [{k: v for k, v in asdict(flow).items() if k != "steps"}
                      for flow in flow_catalog.flows.values()]
        flows_json = json.dumps(flows_dict, ensure_ascii=False, indent=2)

        # 2. 调用 LLM 生成本轮计划 JSON
        prompt = PromptTemplate.from_template(load_prompt("turn_plan"), template_format="jinja2")
        chain = prompt | llm | JsonOutputParser()
        turn_plan_dict = await chain.ainvoke({
            "user_message": rendered_user_message,
            "conversation_history": conversation_history,
            "focused_object_json": focused_object_json,
            "task_state_json": task_state_json,
            "knowledge_intents_json": knowledge_intents_json,
            "flows_json": flows_json,
        })

        # 3. 将计划字典转为 TurnPlan 对象
        turn_plan = TurnPlan.from_dict(turn_plan_dict)
        logger.info("生成本轮计划：{}", turn_plan)
        return turn_plan
