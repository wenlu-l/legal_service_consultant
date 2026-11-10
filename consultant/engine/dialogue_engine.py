"""对话引擎。

编排一轮消息的完整处理流程：
1. 准备当前会话（确保状态中的 Session 有效）；
2. 根据消息类型（文本 / 卡片对象）分流处理；
3. 文本消息：轮次规划 → 计划校验 → 路由到任务 / 知识检索 / 闲聊 / 澄清模块；
4. 卡片消息：设置焦点对象，尝试为活跃任务填槽，失败则澄清；
5. 汇总客服回复，写入会话历史，封装 ProcessResult。
"""
import time
import uuid
from dataclasses import asdict

from consultant.chitchat.chitchat_handler import ChitchatHandler
from consultant.clarify.clarify_responder import ClarifyResponder
from consultant.domain.command import SetSlotsCommand
from consultant.domain.flow_catalog import Flow, FlowStep, CollectSlotStep
from consultant.domain.messages import UserMessage, ProcessResult, MessageType, BotMessage, MessageObject
from consultant.domain.plan import TurnPlan, TurnPlanValidationResult, ClarifyReason
from consultant.domain.state import DialogueState, Turn, FocusedObject
from consultant.knowledge.knowledge_handler import KnowledgeHandler
from consultant.plan.turn_plan_validator import TurnPlanValidator
from consultant.plan.turn_planner import TurnPlanner
from consultant.task.task_handler import TaskHandler


class DialogueEngine:

    def __init__(self, turn_planner: TurnPlanner, turn_plan_validator: TurnPlanValidator,
                 clarify_responder: ClarifyResponder, task_handler: TaskHandler,
                 knowledge_handler: KnowledgeHandler, chit_chat_handler: ChitchatHandler):
        self.turn_planner = turn_planner
        self.turn_plan_validator = turn_plan_validator
        self.clarify_responder = clarify_responder
        self.task_handler = task_handler
        self.knowledge_handler = knowledge_handler
        self.chit_chat_handler = chit_chat_handler

    async def process_message(self, state: DialogueState, user_message: UserMessage) -> ProcessResult:
        """处理本轮消息，得到客服回复"""
        # 1. 准备当前会话
        self._prepare_session(state)
        # 2. 创建本轮对话记录，绑定用户消息（客服回复稍后填充）
        turn = Turn(turn_id=str(uuid.uuid4()), user_message=user_message)
        # 3. 根据消息类型分流
        if user_message.type == MessageType.TEXT:
            # 3.1 处理文本消息
            messages = await self._handle_text_message(state, user_message) or []
        else:
            # 3.2 处理卡片对象消息（课程 / 订单）
            messages = await self._handle_object_message(state, user_message) or []

        # 4. 将客服回复写入轮次，并追加到会话历史
        turn.bot_messages.extend(messages)
        state.shared_state.current_session().turns.append(turn)
        # 5. 封装处理结果
        return ProcessResult(
            sender_id=user_message.sender_id,
            message_id=user_message.message_id,
            messages=messages,
        )

    def _prepare_session(self, state: DialogueState):
        """确保状态中当前 Session 有效（不存在则创建，过期则重建）"""
        current_session = state.shared_state.current_session()
        if current_session is None:
            # 1. 无会话，创建新会话
            state.shared_state.start_session()
        elif time.time() - current_session.last_activity_at > 60 * 60:
            # 2. 会话超时（1 小时），关闭旧会话并清空运行上下文
            state.shared_state.close_current_session()
            state.reset_runtime_for_new_session()
            state.shared_state.start_session()
        else:
            # 3. 会话有效，更新活跃时间
            current_session.last_activity_at = time.time()

    async def _handle_text_message(self, state: DialogueState, user_message: UserMessage) -> list[BotMessage] | None:
        """处理用户文本消息"""
        # 1. 轮次规划
        turn_plan: TurnPlan = await self.turn_planner.predict(
            state, user_message, self.task_handler.flow_catalog, self.knowledge_handler.knowledge_intents
        )
        # 2. 计划校验
        validate_result: TurnPlanValidationResult = self.turn_plan_validator.validate(
            turn_plan, state, self.task_handler.flow_catalog, self.knowledge_handler.knowledge_intents
        )
        # 3. 计划无效，走澄清
        if not validate_result.valid:
            return await self.clarify_responder.respond(validate_result.reason, state, user_message)

        # 4. 计划有效，按方向路由
        messages: list[BotMessage] = []
        if turn_plan.task:
            # 4.1 任务方向
            task_messages = await self.task_handler.handle(turn_plan.task.commands, state, user_message)
            messages.extend(task_messages or [])
        if turn_plan.knowledge:
            # 4.2 知识检索方向（先暂停活跃任务）
            self._pause_active_task(state)
            knowledge_messages = await self.knowledge_handler.handle(turn_plan.knowledge.intents, state, user_message)
            messages.extend(knowledge_messages or [])
        if turn_plan.chitchat:
            # 4.3 闲聊方向（先暂停活跃任务）
            self._pause_active_task(state)
            chitchat_messages = await self.chit_chat_handler.handle(state, user_message)
            messages.extend(chitchat_messages or [])
        return messages if messages else None

    def _pause_active_task(self, state: DialogueState):
        """将活跃任务挂起到暂停列表"""
        active_task = state.task_state.active_task
        if active_task:
            state.task_state.active_task = None
            state.task_state.paused.append(active_task)

    async def _handle_object_message(self, state: DialogueState, user_message: UserMessage) -> list[BotMessage]:
        """处理卡片消息：设置焦点对象并尝试自动填槽"""
        # 1. 将用户发送的卡片（课程/订单）保存为焦点对象
        message_object: MessageObject = user_message.object
        focused_object = FocusedObject(**asdict(message_object))
        state.shared_state.focused_object = focused_object

        # 2. 判断是否能自动填槽
        if self._can_fill_slots_from_focused_object(state):
            # 2.1 可填槽：创建 set_slots 命令，交给任务处理器
            slots_command = SetSlotsCommand(command="set_slots")
            if focused_object.type == "order":
                slots_command.slots = {"order_number": focused_object.id}
            if focused_object.type == "course":
                # 同时兼容 course_id（对象 ID）与 course_name（对象标题）两种槽位名，
                # 因为不同流程的 collect 步骤声明的槽位名不一致，一并写入避免漏填
                slots_command.slots = {
                    "course_id": focused_object.id,
                    "course_name": focused_object.title or focused_object.id,
                }
            return await self.task_handler.handle([slots_command], state, user_message)
        # 2.2 不能填槽：走澄清
        return await self.clarify_responder.respond(
            ClarifyReason.OBJECT_REQUIRES_INTENT, state, user_message
        )

    def _can_fill_slots_from_focused_object(self, state: DialogueState) -> bool:
        """判断焦点对象能否填充活跃任务当前步骤的槽位"""
        # 1. 无活跃任务则不可填槽
        active_task = state.task_state.active_task
        if not active_task:
            return False
        # 2. 获取当前步骤，非 collect 步骤不可填槽
        flow: Flow = self.task_handler.flow_catalog.get_flow(active_task.flow_id)
        step: FlowStep = flow.get_step(active_task.step_id)
        if not isinstance(step, CollectSlotStep):
            return False
        # 3. 槽位名称与焦点对象类型匹配才可填槽
        focused_object = state.shared_state.focused_object
        if step.slot_name == "order_number" and focused_object.type == "order":
            return True
        # 课程卡片可填充 course_id 或 course_name 两种槽位名
        if focused_object.type == "course" and step.slot_name in ("course_id", "course_name"):
            return True
        return False
