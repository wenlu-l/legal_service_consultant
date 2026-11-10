"""任务生命周期响应器。

将任务事件（TaskStarted / TaskSwitched / TaskResumed / TaskCanceled）映射到
system_flows.yml 中的系统流程，执行系统流程生成生命周期提示回复。
"""
from consultant.domain.flow_catalog import FlowCatalog, Flow
from consultant.domain.messages import UserMessage, BotMessage
from consultant.domain.state import DialogueState
from consultant.domain.task_event import TaskEvent, TaskStarted, TaskSwitched, TaskResumed, TaskCanceled
from consultant.task.flow.system_flow_executor import SystemFlowRunner


class TaskLifecycleResponder:

    def __init__(self, flow_catalog: FlowCatalog, system_flow_runner: SystemFlowRunner):
        self.flow_catalog = flow_catalog  # 用户流程清单，用于解析流程名称
        self.system_flow_runner = system_flow_runner  # 系统流程执行器

    async def respond(self, task_events: list[TaskEvent], state: DialogueState,
                      user_message: UserMessage) -> list[BotMessage]:
        """将任务事件列表转为生命周期提示回复列表"""
        messages: list[BotMessage] = []
        for event in task_events:
            flow_id, context = self._map_event(event)
            if flow_id is None:
                continue
            msgs = await self.system_flow_runner.run(flow_id, context, state, user_message)
            messages.extend(msgs)
        return messages

    def _map_event(self, event: TaskEvent):
        """把任务事件映射为系统流程 ID 与上下文"""
        if isinstance(event, TaskStarted):
            return "system_task_started", {"started_flow_name": self._flow_name(event.task.flow_id)}
        if isinstance(event, TaskResumed):
            return "system_task_resumed", {"resumed_flow_name": self._flow_name(event.task.flow_id)}
        if isinstance(event, TaskSwitched):
            return "system_task_interrupted", {
                "interrupted_flow_name": self._flow_name(event.previous.flow_id),
                "started_flow_name": self._flow_name(event.current.flow_id),
            }
        if isinstance(event, TaskCanceled):
            return "system_task_canceled", {"canceled_flow_name": self._flow_name(event.task.flow_id)}
        return None, {}

    def _flow_name(self, flow_id: str) -> str:
        """根据流程 ID 查询流程名称"""
        flow: Flow = self.flow_catalog.get_flow(flow_id)
        return flow.name or flow.id
