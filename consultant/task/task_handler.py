"""任务型对话处理器。

处理任务方向（task 轨道）的消息，流程：
1. 命令处理器把指令应用到状态，产生任务事件列表；
2. 任务生命周期响应器把任务事件转为生命周期提示；
3. 流程推进器推进流程产生客服回复；
4. 合并两类回复返回。
"""
from consultant.domain.command import Command
from consultant.domain.flow_catalog import FlowCatalog
from consultant.domain.messages import UserMessage, BotMessage
from consultant.domain.state import DialogueState
from consultant.domain.task_event import TaskEvent
from consultant.task.command.processor import CommandProcessor
from consultant.task.flow.flow_executor import FlowExecutor
from consultant.task.lifecycle.responder import TaskLifecycleResponder


class TaskHandler:

    def __init__(self, command_processor: CommandProcessor,
                 task_lifecycle_responder: TaskLifecycleResponder,
                 flow_executor: FlowExecutor, flow_catalog: FlowCatalog):
        self.command_processor = command_processor
        self.task_lifecycle_responder = task_lifecycle_responder
        self.flow_executor = flow_executor
        self.flow_catalog = flow_catalog

    async def handle(self, commands: list[Command], state: DialogueState,
                     user_message: UserMessage) -> list[BotMessage]:
        """处理任务方向指令，返回客服回复列表"""
        all_bot_messages: list[BotMessage] = []

        # 1. 命令应用到状态，产生任务事件列表
        task_events: list[TaskEvent] = self.command_processor.run(
            commands=commands, state=state, flow_catalog=self.flow_catalog
        )

        # 2. 任务事件转为生命周期提示（走 system_flows.yml）
        tips = await self.task_lifecycle_responder.respond(task_events, state, user_message)
        all_bot_messages.extend(tips)

        # 3. 流程推进器推进流程，产生客服回复
        flow_msgs = await self.flow_executor.run_task(
            state=state, user_message=user_message, flow_catalog=self.flow_catalog
        )
        all_bot_messages.extend(flow_msgs)

        return all_bot_messages
