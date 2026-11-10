"""用户流程执行器。

推进某个任务流程的步骤（start / response / collect / action / end），产出客服回复：
- start：仅作开始标识，直接推进；
- response：渲染回复模板生成客服回复；
- collect：收集槽位，槽位缺失时追问（走 system_collect_information 系统流程）；
- action：调用业务动作，将返回结果回填槽位；
- end：清理活跃任务与焦点对象，结束流程。
"""
from typing import Any

from loguru import logger

from consultant.domain.action import ActionResult
from consultant.domain.flow_catalog import (
    FlowCatalog, Flow, FlowStep, StartFlowStep, ResponseFlowStep, CollectSlotStep,
    ActionFlowStep, EndFlowStep, StaticLink, ConditionLink, FallbackLink,
)
from consultant.domain.messages import UserMessage, BotMessage
from consultant.domain.state import DialogueState
from consultant.task.action.action_runner import ActionRunner
from consultant.task.response.response_renderer import ResponseRenderer


class FlowExecutor:

    def __init__(self, action_runner: ActionRunner, response_renderer: ResponseRenderer,
                 system_flow_runner=None, max_count: int = 100):
        self.action_runner = action_runner
        self.response_renderer = response_renderer
        self.system_flow_runner = system_flow_runner
        self.max_count = max_count

    async def run_task(self, state: DialogueState, user_message: UserMessage,
                       flow_catalog: FlowCatalog) -> list[BotMessage] | None:
        """循环处理不同步骤类型，最多循环 max_count 次，返回客服回复列表"""
        bot_messages: list[BotMessage] = []

        for _ in range(self.max_count):
            # 1. 获取当前活跃任务，不存在则直接返回累计回复
            active_task = state.task_state.active_task
            if active_task is None:
                return bot_messages

            # 2. 根据活跃任务的 flow_id / step_id 获取流程与当前步骤
            flow: Flow = flow_catalog.get_flow(active_task.flow_id)
            step: FlowStep = flow.get_step(active_task.step_id)
            logger.info("流程推进器，当前流程：{}，当前步骤：{}", flow.name, step.id)

            # 3. 处理 start 步骤：仅推进
            if isinstance(step, StartFlowStep):
                self._advance(step, state)
                continue

            # 4. 处理 response 步骤：渲染回复
            if isinstance(step, ResponseFlowStep):
                bot_message = await self.response_renderer.respond(step.template, state, user_message)
                bot_messages.append(bot_message)
                self._advance(step, state)
                continue

            # 5. 处理 collect 步骤：收集槽位
            if isinstance(step, CollectSlotStep):
                should_wait = await self._run_collect(step, state, user_message, bot_messages)
                if should_wait:
                    # 需要等待用户输入，返回追问消息
                    return bot_messages
                self._advance(step, state)
                continue

            # 6. 处理 action 步骤：调用业务动作并回填槽位
            if isinstance(step, ActionFlowStep):
                action_result: ActionResult = await self.action_runner.run(step.action, state)
                state.task_state.set_slots(action_result.slot_updates)
                self._advance(step, state)
                continue

            # 7. 处理 end 步骤：清理并结束流程
            if isinstance(step, EndFlowStep):
                state.task_state.active_task = None
                state.shared_state.focused_object = None
                return bot_messages

    def _advance(self, step: FlowStep, state: DialogueState):
        """流程推进：本质上修改活跃任务的 step_id"""
        for link in step.next:
            # 固定跳转
            if isinstance(link, StaticLink):
                state.task_state.active_task.step_id = link.target
                return
            # 条件跳转：满足条件才跳转
            if isinstance(link, ConditionLink) and self.condition_validate(
                link.condition, {"slots": state.task_state.active_task.slots}
            ):
                state.task_state.active_task.step_id = link.target
                return
            # 兜底跳转
            if isinstance(link, FallbackLink):
                state.task_state.active_task.step_id = link.target
                return

    def condition_validate(self, condition: str, data: dict[str, Any]) -> bool:
        """判断条件表达式是否成立"""
        return bool(eval(condition, {"__builtins__": {}}, data))

    async def _run_collect(self, step: CollectSlotStep, state: DialogueState,
                           user_message: UserMessage, bot_messages: list[BotMessage]) -> bool:
        """处理收集槽位步骤，返回 True 表示需等待用户输入"""
        # 1. 从当前任务槽位获取该步骤需要的槽位值
        slot_value = state.task_state.active_task.slots.get(step.slot_name)
        if slot_value is None:
            # 1.1 尝试从焦点对象填槽
            self._try_fill_slot_from_focused_object(step, state)
        slot_value = state.task_state.active_task.slots.get(step.slot_name)

        # 2. 填槽失败则追问用户
        if slot_value is None:
            await self._ask_via_system_flow(step.template, state, user_message, bot_messages)
            return True

        # 3. 填槽成功，无需校验则继续推进
        if not step.validation:
            return False

        # 4. 需要校验
        result = self.condition_validate(step.validation.condition, {"slots": state.task_state.active_task.slots})
        if result:
            # 4.1 校验通过，继续推进
            return False
        # 4.2 校验失败：移除槽位并返回失败提示
        state.task_state.active_task.slots.pop(step.slot_name)
        await self._ask_via_system_flow(step.validation.failure_template, state, user_message, bot_messages)
        return True

    async def _ask_via_system_flow(self, template, state: DialogueState,
                                   user_message: UserMessage, bot_messages: list[BotMessage]):
        """追问统一走 system_collect_information 系统流程（action_response + action_listen）"""
        if self.system_flow_runner is not None:
            # 将追问模板封装为 context.response 传给系统流程
            response_spec = {
                "mode": template.mode.value,
                "text": template.text,
                "prompt": template.prompt,
            }
            msgs = await self.system_flow_runner.run(
                "system_collect_information",
                {"response": response_spec},
                state, user_message,
            )
            bot_messages.extend(msgs)
        else:
            # 兜底：直接渲染追问模板
            bot_message = await self.response_renderer.respond(template, state, user_message)
            bot_messages.append(bot_message)

    def _try_fill_slot_from_focused_object(self, step: CollectSlotStep, state: DialogueState):
        """从焦点对象（课程/订单卡片）填充槽位"""
        focused_object = state.shared_state.focused_object
        if focused_object is None:
            return
        # 订单卡片填充 order_number
        if step.slot_name == "order_number" and focused_object.type == "order":
            state.task_state.set_slots({step.slot_name: focused_object.id})
        # 课程卡片填充 course_id / course_name
        if focused_object.type == "course" and step.slot_name in ("course_id", "course_name"):
            if step.slot_name == "course_name":
                state.task_state.set_slots({step.slot_name: focused_object.title or focused_object.id})
            else:
                state.task_state.set_slots({step.slot_name: focused_object.id})
