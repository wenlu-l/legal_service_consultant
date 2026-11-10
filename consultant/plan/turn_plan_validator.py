"""轮次计划校验器。

对 TurnPlanner 产生的计划进行校验，确保：
- 只命中一个方向（task / knowledge / chitchat）；
- task 方向：指令非空、流程 ID / 槽位名称 / 任务 ID 系统支持；
- knowledge 方向：意图 ID 系统支持，且满足焦点对象要求。

校验失败返回对应的 ClarifyReason，由 ClarifyResponder 生成澄清回复。
"""
from consultant.domain.command import StartFlowCommand, Command, ResumeTaskCommand, SetSlotsCommand, CancelTaskCommand
from consultant.domain.flow_catalog import FlowCatalog
from consultant.domain.knowledge import KnowledgeIntent
from consultant.domain.plan import (
    TurnPlan, TurnPlanValidationResult, ClarifyReason, TaskTurnPlan, KnowledgeTurnPlan,
)
from consultant.domain.state import DialogueState


class TurnPlanValidator:

    def validate(self, turn_plan: TurnPlan, state: DialogueState, flow_catalog: FlowCatalog,
                 knowledge_intents: dict[str, KnowledgeIntent]) -> TurnPlanValidationResult:
        """校验轮次计划，返回校验结果。

        方向组合规则：
        - 没有任何方向 → 不合法（MISSING_TRACK）；
        - chitchat 与 task / knowledge 任一共存 → 不合法（闲聊必须独占）；
        - task 与 knowledge 可以同时命中（多场景问询，串行处理）；
        - 命中的每个方向都要通过各自的细分校验。
        """
        has_task = turn_plan.task is not None
        has_knowledge = turn_plan.knowledge is not None
        has_chitchat = turn_plan.chitchat is not None

        # 1. 无方向不合法
        if not (has_task or has_knowledge or has_chitchat):
            return TurnPlanValidationResult(valid=False, reason=ClarifyReason.MISSING_TRACK)

        # 2. 闲聊必须独占，不能和业务/知识混在一起
        if has_chitchat and (has_task or has_knowledge):
            return TurnPlanValidationResult(valid=False, reason=ClarifyReason.MULTIPLE_TRACKS)

        # 3. 逐个校验命中的方向（task 与 knowledge 可同时存在）
        if has_task:
            task_result = self._validate_task(turn_plan.task, state, flow_catalog)
            if not task_result.valid:
                return task_result

        if has_knowledge:
            knowledge_result = self._validate_knowledge(turn_plan.knowledge, knowledge_intents, state)
            if not knowledge_result.valid:
                return knowledge_result

        return TurnPlanValidationResult(valid=True)

    def _validate_task(self, task_turn_plan: TaskTurnPlan, state: DialogueState,
                       flow_catalog: FlowCatalog) -> TurnPlanValidationResult:
        """校验任务方向的指令"""
        # 1. 指令不能为空
        if not task_turn_plan.commands:
            return TurnPlanValidationResult(valid=False, reason=ClarifyReason.MISSING_TASK_COMMANDS)

        # 2. 启动流程 / 恢复任务指令最多一个
        start_flow_commands = [c for c in task_turn_plan.commands if isinstance(c, StartFlowCommand)]
        if start_flow_commands and len(start_flow_commands) != 1:
            return TurnPlanValidationResult(valid=False, reason=ClarifyReason.MULTIPLE_START_COMMANDS)

        resume_task_commands = [c for c in task_turn_plan.commands if isinstance(c, ResumeTaskCommand)]
        if resume_task_commands and len(resume_task_commands) != 1:
            return TurnPlanValidationResult(valid=False, reason=ClarifyReason.MULTIPLE_RESUME_COMMANDS)

        # 3. 逐条校验指令
        for command in task_turn_plan.commands:
            # 3.1 流程 ID 必须系统支持
            if isinstance(command, StartFlowCommand):
                if command.flow not in flow_catalog.flows:
                    return TurnPlanValidationResult(valid=False, reason=ClarifyReason.INVALID_TASK_COMMAND)

            # 3.2 槽位名称必须系统支持
            if isinstance(command, SetSlotsCommand):
                for slot_name in command.slots.keys():
                    if slot_name not in flow_catalog.slots:
                        return TurnPlanValidationResult(valid=False, reason=ClarifyReason.INVALID_TASK_COMMAND)

            # 3.3 恢复的任务必须在暂停列表中
            if isinstance(command, ResumeTaskCommand):
                paused_task_ids = [t.task_id for t in state.task_state.paused]
                if command.task_id not in paused_task_ids:
                    return TurnPlanValidationResult(valid=False, reason=ClarifyReason.INVALID_TASK_COMMAND)

            # 3.4 取消的任务必须是活跃任务或暂停任务
            if isinstance(command, CancelTaskCommand):
                all_task_ids = [t.task_id for t in state.task_state.paused]
                if state.task_state.active_task:
                    all_task_ids.append(state.task_state.active_task.task_id)
                if command.task_id not in all_task_ids:
                    return TurnPlanValidationResult(valid=False, reason=ClarifyReason.INVALID_TASK_COMMAND)

        return TurnPlanValidationResult(valid=True)

    def _validate_knowledge(self, knowledge_turn_plan: KnowledgeTurnPlan,
                            knowledge_intents: dict[str, KnowledgeIntent],
                            state: DialogueState) -> TurnPlanValidationResult:
        """校验知识方向的意图"""
        # 1. 意图不能为空
        if not knowledge_turn_plan.intents:
            return TurnPlanValidationResult(valid=False, reason=ClarifyReason.MISSING_KNOWLEDGE_INTENT)

        # 2. 逐条校验意图
        for intent_id in knowledge_turn_plan.intents:
            # 2.1 意图 ID 必须系统支持
            if intent_id not in knowledge_intents:
                return TurnPlanValidationResult(valid=False, reason=ClarifyReason.UNKNOWN_KNOWLEDGE_INTENT)

            # 2.2 意图要求焦点对象时，校验焦点对象类型
            intent: KnowledgeIntent = knowledge_intents.get(intent_id)
            requires_object = intent.requires_object
            focused_object = state.shared_state.focused_object
            if requires_object and (focused_object is None or focused_object.type != requires_object):
                return TurnPlanValidationResult(valid=False, reason=ClarifyReason.MISSING_FOCUSED_OBJECT)

        return TurnPlanValidationResult(valid=True)
