"""任务事件数据类。

任务事件由命令处理器（CommandProcessor）在修改任务状态时产生，用于生成系统生命周期提示，
例如：
- 任务启动提示：好的，我们先处理「订单查询」
- 任务切换提示：好的，先把「退款申请」放一放，先处理「订单查询」
- 任务取消提示：好的，「退款申请」已帮您取消
- 任务恢复提示：好的，继续为您办理「退款申请」
"""
from dataclasses import dataclass
from typing import TypeAlias


@dataclass
class TaskRef:
    """任务实例引用：流程 ID + 任务 ID"""
    flow_id: str
    task_id: str


@dataclass
class TaskStarted:
    """任务开始执行"""
    task: TaskRef


@dataclass
class TaskSwitched:
    """从上一个任务切换到当前任务（持有旧、新两个引用）"""
    previous: TaskRef
    current: TaskRef


@dataclass
class TaskResumed:
    """暂停的任务被恢复"""
    task: TaskRef


@dataclass
class TaskCanceled:
    """任务被取消"""
    task: TaskRef


# 任务事件联合类型
TaskEvent: TypeAlias = TaskStarted | TaskSwitched | TaskResumed | TaskCanceled
