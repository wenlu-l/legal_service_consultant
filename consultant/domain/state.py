"""对话状态数据类。

对话状态（DialogueState）是某个用户所有对话相关信息的集合，对应数据库 dialogue_states
表中 state_json 字段。包含两部分：
1. 共享状态（SharedState）：焦点对象（课程/订单卡片）+ 会话列表（Session/轮次 Turn）；
2. 任务状态（TaskState）：当前正在处理的任务实例 + 被暂停的任务实例列表。

其中任务实例（TaskInstance）基于 yaml 编排流程定义产生，例如退款任务、订单查询任务等。
"""
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from consultant.domain.messages import UserMessage, BotMessage
from consultant.domain.task_event import TaskEvent, TaskStarted, TaskRef, TaskSwitched, TaskCanceled, TaskResumed


@dataclass
class Turn:
    """一轮对话：用户消息 + 客服回复"""
    turn_id: str  # 轮次 ID
    user_message: UserMessage  # 用户消息
    bot_messages: list[BotMessage] = field(default_factory=list)  # 客服回复


@dataclass
class Session:
    """会话（间隔阈值 1 小时）"""
    session_id: str  # 会话 ID
    started_at: float  # 会话创建时间
    last_activity_at: float  # 最近活跃时间
    closed_at: float | None = None  # 会话关闭时间
    turns: list[Turn] = field(default_factory=list)  # 会话内所有对话轮次


@dataclass
class FocusedObject:
    """焦点对象（卡片）：课程或订单"""
    type: str  # course 课程 / order 订单
    id: str  # 课程 ID 或订单号
    title: str | None = None  # 标题
    attributes: dict[str, Any] = field(default_factory=dict)  # 附加属性


@dataclass
class SharedState:
    """共享状态：焦点对象 + 会话列表"""
    focused_object: FocusedObject | None = None  # 焦点对象
    sessions: list[Session] = field(default_factory=list)  # 某用户的所有会话

    def current_session(self) -> Session | None:
        """获取当前用户最新会话"""
        if self.sessions:
            return self.sessions[-1]
        return None

    def start_session(self):
        """创建新会话并加入会话列表"""
        now = time.time()
        session = Session(
            session_id=str(uuid.uuid4()),
            started_at=now,
            last_activity_at=now,
        )
        self.sessions.append(session)

    def close_current_session(self):
        """关闭当前会话"""
        session = self.current_session()
        if session is not None:
            session.closed_at = time.time()


@dataclass
class TaskInstance:
    """基于 yaml 流程产生的任务实例，例如退款任务、查询订单任务等"""
    flow_id: str  # 流程 ID
    step_id: str  # 当前执行到的步骤 ID
    slots: dict[str, Any] = field(default_factory=dict)  # 已收集到的槽位及取值
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # 任务实例 ID

    def to_ref(self) -> TaskRef:
        """生成任务引用"""
        return TaskRef(flow_id=self.flow_id, task_id=self.task_id)


@dataclass
class TaskState:
    """任务状态"""
    active_task: TaskInstance | None = None  # 正在处理的任务实例
    paused: list[TaskInstance] = field(default_factory=list)  # 被暂停的任务实例列表

    def start(self, task: TaskInstance) -> TaskEvent:
        """启动任务：无活跃任务产生 TaskStarted，否则产生 TaskSwitched"""
        if self.active_task is None:
            # 1. 当前无活跃任务，直接启动
            self.active_task = task
            return TaskStarted(task=task.to_ref())
        # 2. 已有活跃任务，将其挂起，再启动新任务
        previous = self.active_task
        self.paused.append(previous)
        self.active_task = task
        return TaskSwitched(previous=previous.to_ref(), current=task.to_ref())

    def set_slots(self, slots: dict[str, Any]):
        """为当前任务填充槽位值"""
        if self.active_task is not None:
            self.active_task.slots.update(slots)

    def cancel(self, task_id: str) -> TaskEvent:
        """取消指定任务（活跃任务或暂停任务）"""
        if self.active_task and self.active_task.task_id == task_id:
            # 1. 取消的是当前活跃任务
            cancel = self.active_task
            self.active_task = None
            return TaskCanceled(task=cancel.to_ref())
        # 2. 取消的是暂停列表中的任务
        cancel = next(t for t in self.paused if t.task_id == task_id)
        self.paused.remove(cancel)
        return TaskCanceled(task=cancel.to_ref())

    def resume(self, task_id: str) -> TaskEvent:
        """从暂停列表恢复指定任务"""
        # 1. 从暂停列表移除要恢复的任务
        resume = next(t for t in self.paused if t.task_id == task_id)
        self.paused.remove(resume)
        if self.active_task:
            # 2. 有活跃任务则产生任务切换事件
            previous = self.active_task
            self.paused.append(self.active_task)
            self.active_task = resume
            return TaskSwitched(previous=previous.to_ref(), current=resume.to_ref())
        # 3. 无活跃任务则产生任务恢复事件
        self.active_task = resume
        return TaskResumed(task=resume.to_ref())


@dataclass
class DialogueState:
    """对话状态：与 dialogue_states 表中 state_json 对应"""
    sender_id: str  # 用户 ID
    shared_state: SharedState = field(default_factory=SharedState)  # 共享状态
    task_state: TaskState = field(default_factory=TaskState)  # 任务状态

    def reset_runtime_for_new_session(self):
        """开启新会话时清空运行上下文：焦点对象、活跃任务、暂停任务列表"""
        self.shared_state.focused_object = None
        self.task_state.active_task = None
        self.task_state.paused.clear()
