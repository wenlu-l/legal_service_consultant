"""对话引擎组装器。

在项目启动时组装 DialogueEngine：加载用户流程（user_flows.yml）与系统流程
（system_flows.yml），创建命令处理器、响应渲染器、动作执行器、流程执行器、
生命周期响应器、知识处理器等，最终装配为对话引擎单例。
"""
from pathlib import Path

from consultant.chitchat.chitchat_handler import ChitchatHandler
from consultant.chitchat.chitchat_responder import ChitchatResponder
from consultant.clarify.clarify_responder import ClarifyResponder
from consultant.domain.knowledge import KNOWLEDGE_INTENTS
from consultant.engine.dialogue_engine import DialogueEngine
from consultant.knowledge.knowledge_handler import KnowledgeHandler
from consultant.knowledge.providers import KnowledgeProvider, build_default_providers
from consultant.knowledge.responder import KnowledgeResponder
from consultant.plan.turn_plan_validator import TurnPlanValidator
from consultant.plan.turn_planner import TurnPlanner
from consultant.task.action.builder import build_action_runner
from consultant.task.command.processor import CommandProcessor
from consultant.task.flow.flow_executor import FlowExecutor
from consultant.task.flow.load_flow import FlowLoader
from consultant.task.flow.system_flow_executor import SystemFlowRunner
from consultant.task.lifecycle.responder import TaskLifecycleResponder
from consultant.task.response.response_renderer import ResponseRenderer
from consultant.task.task_handler import TaskHandler


def build_engine() -> DialogueEngine:
    """组装对话引擎"""
    # 1. 加载流程清单（用户流程 + 系统流程）
    root = Path(__file__).parents[2]
    user_flow_path = root / "user_flows.yml"
    system_flow_path = root / "system_flows.yml"
    loader = FlowLoader()
    user_catalog = loader.load_many([user_flow_path])
    system_catalog = loader.load_many([system_flow_path])

    # 2. 构建任务处理链路
    command_processor = CommandProcessor()
    response_renderer = ResponseRenderer()
    system_flow_runner = SystemFlowRunner(system_catalog, response_renderer)

    action_runner = build_action_runner()
    flow_executor = FlowExecutor(action_runner, response_renderer, system_flow_runner=system_flow_runner)

    lifecycle_responder = TaskLifecycleResponder(user_catalog, system_flow_runner)
    task_handler = TaskHandler(command_processor, lifecycle_responder, flow_executor, user_catalog)

    # 3. 构建知识检索链路
    knowledge_intents = KNOWLEDGE_INTENTS
    providers: list[KnowledgeProvider] = build_default_providers()
    knowledge_responder = KnowledgeResponder()
    knowledge_handler = KnowledgeHandler(knowledge_intents, providers, knowledge_responder)

    # 4. 装配对话引擎
    return DialogueEngine(
        turn_planner=TurnPlanner(),
        turn_plan_validator=TurnPlanValidator(),
        clarify_responder=ClarifyResponder(),
        task_handler=task_handler,
        knowledge_handler=knowledge_handler,
        chit_chat_handler=ChitchatHandler(ChitchatResponder()),
    )
