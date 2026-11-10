"""Action 注册中心。

把所有自定义 Action 对象注入容器，对外提供注册（register）与获取（get）方法。
"""
from consultant.domain.action import Action


class ActionRegistry:
    """Action 注册中心"""

    def __init__(self):
        self._actions: dict[str, Action] = {}

    def register(self, action: Action):
        """将 Action 对象注入注册中心，key 为 Action.name"""
        self._actions[action.name] = action

    def get(self, action_name: str) -> Action | None:
        """根据 Action 名称获取 Action 对象"""
        return self._actions.get(action_name)
