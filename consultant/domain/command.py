"""任务指令数据类。

LLM 轮次规划（TurnPlanner）会产出一批指令（Command），命令处理器（CommandProcessor）
按指令类型把指令应用到对话状态上，产生对应的任务事件。四种指令：
- start_flow：启动流程
- set_slots：填充槽位
- cancel_task：取消任务
- resume_task：恢复暂停任务
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Command:
    """指令父类"""
    command: str  # 指令类型名称，与 COMMAND_NAME_TO_CLASS 的 key 对应

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Command":
        """将 LLM 产生的指令字典转为对应的命令对象"""
        clz = COMMAND_NAME_TO_CLASS.get(data.get("command"))
        return clz(**data)


@dataclass
class StartFlowCommand(Command):
    """启动任务指令"""
    flow: str  # 流程 ID


@dataclass
class SetSlotsCommand(Command):
    """设置槽位指令"""
    slots: dict[str, Any] = field(default_factory=dict)  # 用户提交的槽位取值


@dataclass
class CancelTaskCommand(Command):
    """取消任务指令"""
    task_id: str  # 被取消的任务 ID


@dataclass
class ResumeTaskCommand(Command):
    """恢复任务指令"""
    task_id: str  # 要恢复的任务 ID


# 指令名称与指令类的映射
COMMAND_NAME_TO_CLASS: dict[str, type[Command]] = {
    "start_flow": StartFlowCommand,
    "set_slots": SetSlotsCommand,
    "cancel_task": CancelTaskCommand,
    "resume_task": ResumeTaskCommand,
}
