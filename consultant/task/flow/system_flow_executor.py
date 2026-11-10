"""系统流程执行器。

执行 system_flows.yml 中定义的系统级流程，支持两类内置动作：
- action_response：渲染回复（static 直接渲染 / rephrase 渲染后再由 LLM 润色）；
- action_listen：结束本轮、等待用户输入。

用于任务生命周期提示（启动/切换/取消/恢复）和槽位追问等场景。
"""
from consultant.domain.flow_catalog import (
    FlowCatalog, Flow, FlowStep, ActionFlowStep, EndFlowStep,
    StaticLink, ConditionLink, FallbackLink, ResponseMode,
)
from consultant.domain.messages import UserMessage, BotMessage
from consultant.domain.state import DialogueState
from consultant.task.response.response_renderer import ResponseRenderer


class SystemFlowRunner:

    def __init__(self, system_catalog: FlowCatalog, response_renderer: ResponseRenderer):
        self.system_catalog = system_catalog
        self.response_renderer = response_renderer

    async def run(self, flow_id: str, context: dict, state: DialogueState,
                  user_message: UserMessage) -> list[BotMessage]:
        """执行指定系统流程，返回客服回复列表"""
        flow: Flow | None = self.system_catalog.get_flow(flow_id)
        if flow is None:
            return []
        messages: list[BotMessage] = []
        step: FlowStep | None = flow.get_start_step()

        # 循环推进步骤，最多 100 次
        for _ in range(100):
            if step is None or isinstance(step, EndFlowStep):
                return messages

            if isinstance(step, ActionFlowStep):
                if step.action == "action_response":
                    # 渲染回复
                    spec = self._resolve_response_spec(step.args, context)
                    if spec:
                        mode = ResponseMode(spec.get("mode", "static"))
                        bot = await self.response_renderer.render(
                            mode, spec.get("text", ""), spec.get("prompt", ""),
                            state, user_message, context=context,
                        )
                        messages.append(bot)
                elif step.action == "action_listen":
                    # 等待用户输入，结束本轮
                    return messages

            step = self._next_step(flow, step, state, context)
        return messages

    def _resolve_response_spec(self, args, context: dict):
        """解析 action_response 的 args：字典直接使用，context.xxx 则从上下文取值"""
        if isinstance(args, dict):
            return args
        if isinstance(args, str) and args.startswith("context."):
            key = args.split(".", 1)[1]
            return context.get(key)
        return None

    def _next_step(self, flow: Flow, step: FlowStep, state: DialogueState, context: dict) -> FlowStep | None:
        """根据连接线确定下一个步骤"""
        slots = state.task_state.active_task.slots if state.task_state.active_task else {}
        data = {"slots": slots, "context": context}
        for link in step.next:
            if isinstance(link, StaticLink):
                return flow.get_step(link.target)
            if isinstance(link, ConditionLink) and self._eval(link.condition, data):
                return flow.get_step(link.target)
            if isinstance(link, FallbackLink):
                return flow.get_step(link.target)
        return None

    @staticmethod
    def _eval(condition: str, data: dict) -> bool:
        """求值条件表达式"""
        return bool(eval(condition, {"__builtins__": {}}, data))
