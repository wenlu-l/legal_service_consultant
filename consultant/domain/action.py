"""业务动作（Action）抽象基类。

Action 对应用户流程（user_flows.yml）中 type 为 action 的步骤，负责调用后端
（当前为演示数据）获取业务结果，并通过 ActionResult.slot_updates 回填槽位。
所有自定义 Action 需继承 Action 并实现 run 方法，name 属性与流程步骤中 action 取值一致。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from consultant.domain.state import DialogueState


@dataclass
class ActionResult:
    """调用 Action 返回结果，通过 slot_updates 回填槽位"""
    slot_updates: dict[str, Any] = field(default_factory=dict)


class Action(ABC):
    """所有 Action 的父类"""
    name: str  # Action 名称，与 action 步骤的 action 取值一致

    @abstractmethod
    async def run(self, state: DialogueState) -> ActionResult:
        """执行业务动作，返回槽位更新结果"""
        pass
