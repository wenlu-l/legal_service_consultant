"""轮次计划（TurnPlan）与计划校验结果数据类。

TurnPlanner 调用 LLM 生成本轮计划，计划最多命中一个方向（task / knowledge / chitchat）。
TurnPlanValidator 对计划进行校验，校验失败时返回对应的 ClarifyReason 原因，
由 ClarifyResponder 生成澄清回复。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from consultant.domain.command import Command


@dataclass
class ChitchatTurnPlan:
    """闲聊方向（无额外参数）"""
    pass


@dataclass
class KnowledgeTurnPlan:
    """知识检索方向"""
    intents: list[str] = field(default_factory=list)  # 知识意图 ID 列表

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeTurnPlan":
        return cls(**data)


@dataclass
class TaskTurnPlan:
    """任务处理方向"""
    commands: list[Command] = field(default_factory=list)  # 指令列表

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskTurnPlan":
        return cls(commands=[Command.from_dict(d) for d in data.get("commands", [])])


@dataclass
class TurnPlan:
    """本轮轮次计划，最多命中一个方向"""
    task: TaskTurnPlan | None = None
    knowledge: KnowledgeTurnPlan | None = None
    chitchat: ChitchatTurnPlan | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TurnPlan":
        return cls(
            task=TaskTurnPlan.from_dict(data["task"]) if data.get("task") is not None else None,
            knowledge=KnowledgeTurnPlan.from_dict(data["knowledge"]) if data.get("knowledge") is not None else None,
            chitchat=ChitchatTurnPlan() if data.get("chitchat") is not None else None,
        )


class ClarifyReason(str, Enum):
    """轮次计划校验失败原因枚举"""
    MISSING_TRACK = "missing_track"  # 没有任何方向
    MULTIPLE_TRACKS = "multiple_tracks"  # 命中多个方向
    MISSING_TASK_COMMANDS = "missing_task_commands"  # 任务方向但指令为空
    MULTIPLE_START_COMMANDS = "multiple_start_commands"  # 多个启动任务指令
    MULTIPLE_RESUME_COMMANDS = "multiple_resume_commands"  # 多个恢复任务指令
    MISSING_KNOWLEDGE_INTENT = "missing_knowledge_intent"  # 知识方向但意图为空
    MISSING_FOCUSED_OBJECT = "missing_focused_object"  # 知识意图要求焦点对象但缺失
    OBJECT_REQUIRES_INTENT = "object_requires_intent"  # 卡片消息但无法为任务填充槽位
    INVALID_TASK_COMMAND = "invalid_task_command"  # 任务指令系统不识别
    UNKNOWN_KNOWLEDGE_INTENT = "unknown_knowledge_intent"  # 知识意图系统不支持


@dataclass
class TurnPlanValidationResult:
    """轮次计划校验结果"""
    valid: bool  # True 表示校验通过
    reason: ClarifyReason | None = None  # 校验失败的具体原因
