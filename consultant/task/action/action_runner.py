"""Action 执行器。

根据 action 名称从注册中心获取 Action 对象，调用其 run 方法返回结果。
"""
from consultant.domain.action import ActionResult, Action
from consultant.domain.state import DialogueState
from consultant.task.action.registry import ActionRegistry


class ActionRunner:

    def __init__(self, registry: ActionRegistry):
        self.registry = registry

    async def run(self, action_name: str, state: DialogueState) -> ActionResult:
        """根据名称获取 Action 并执行，返回 ActionResult"""
        # 1. 从注册中心获取 Action 对象
        action: Action = self.registry.get(action_name)
        # 2. 调用 Action.run 返回结果
        return await action.run(state)
