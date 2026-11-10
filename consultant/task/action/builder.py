"""Action 组装器。

自动发现 custom 包下所有符合规范的 Action 子类并注册，返回 ActionRunner。
"""
import importlib
import inspect
import pkgutil

from consultant.domain.action import Action
from consultant.task.action.action_runner import ActionRunner
from consultant.task.action.registry import ActionRegistry


def register_custom_actions_to_registry() -> ActionRegistry:
    """自动扫描 custom 包下符合规范的 Action 类并注册到注册中心"""
    registry = ActionRegistry()

    # 1. 导入 custom 包，获取包对象
    package = importlib.import_module("consultant.task.action.custom")

    # 2. 遍历 custom 包下所有模块（prefix 用于拼接完整模块名）
    for _, module_name, is_package in pkgutil.iter_modules(
        package.__path__, prefix=f"{package.__name__}."
    ):
        # 2.1 过滤掉子包
        if is_package:
            continue
        # 2.2 导入模块
        module = importlib.import_module(module_name)

        # 2.3 遍历模块中的类，筛选 Action 子类
        for _, action_class in inspect.getmembers(module, inspect.isclass):
            # 2.4 过滤掉非 Action 子类以及 Action 本身
            if not issubclass(action_class, Action) or action_class is Action:
                continue
            # 2.5 只保留定义在当前模块中的类（排除 import 进来的类）
            if action_class.__module__ != module.__name__:
                continue
            # 2.6 注册 Action 实例
            registry.register(action_class())

    return registry


def build_action_runner() -> ActionRunner:
    """项目启动时调用：扫描注册自定义 Action，返回 ActionRunner"""
    # 1. 扫描并注册自定义 Action
    registry = register_custom_actions_to_registry()
    # 2. 将注册中心注入 ActionRunner
    return ActionRunner(registry)
