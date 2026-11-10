"""命令处理器。

把 LLM 轮次规划产生的指令列表应用到对话状态，返回任务事件列表，用于生成生命周期提示。
支持四种指令：start_flow（启动流程）、set_slots（填充槽位）、cancel_task（取消任务）、
resume_task（恢复任务）。
"""
from loguru import logger

from consultant.domain.command import Command, StartFlowCommand, SetSlotsCommand, CancelTaskCommand, ResumeTaskCommand
from consultant.domain.flow_catalog import FlowCatalog, Flow, FlowStep
from consultant.domain.state import DialogueState, TaskInstance
from consultant.domain.task_event import TaskEvent


class CommandProcessor:

    def run(self, commands: list[Command], state: DialogueState, flow_catalog: FlowCatalog) -> list[TaskEvent]:
        """遍历指令列表，将指令应用到状态，返回任务事件列表"""
        events: list[TaskEvent] = []
        for command in commands:
            event = self._apply(command, state, flow_catalog)
            logger.info("命令处理器，已处理命令：{}，得到任务事件：{}", command, event)
            if event:
                events.append(event)
        return events

    def _apply(self, command: Command, state: DialogueState, flow_catalog: FlowCatalog) -> TaskEvent | None:
        """将单个指令应用到状态，返回任务事件"""
        if isinstance(command, StartFlowCommand):
            # 1. 根据流程 ID 获取流程配置
            flow: Flow = flow_catalog.get_flow(command.flow)
            # 2. 获取流程的起始步骤
            start_step: FlowStep = flow.get_start_step()
            # 3. 创建任务实例
            task = TaskInstance(flow_id=flow.id, step_id=start_step.id)
            # 4. 启动任务，返回任务事件
            return state.task_state.start(task)

        if isinstance(command, SetSlotsCommand):
            # 存在活跃任务才填充槽位（不产生任务事件）
            if state.task_state.active_task:
                state.task_state.set_slots(command.slots)
            return None

        if isinstance(command, CancelTaskCommand):
            return state.task_state.cancel(command.task_id)

        if isinstance(command, ResumeTaskCommand):
            return state.task_state.resume(command.task_id)

        return None
