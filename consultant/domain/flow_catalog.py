"""流程定义（Flow Catalog）数据类。

负责把 user_flows.yml / system_flows.yml 中的流程配置解析为 Python 对象，包括：
- ResponseTemplate：回复模板（static 直接渲染 / rephrase 渲染后再由 LLM 润色）；
- FlowStep 五类步骤：start / action / response / collect / end；
- FlowStepLink 连接线：static 固定跳转 / condition 条件跳转 / fallback 兜底跳转；
- Flow：单个流程定义；FlowCatalog：全部流程清单。

解析入口是 FlowLoader（见 task/flow/load_flow.py）。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResponseMode(Enum):
    """回复渲染模式"""
    STATIC = "static"        # 渲染后直接返回
    REPHRASE = "rephrase"    # 先渲染基础回复，再调用 LLM 润色


@dataclass
class ResponseTemplate:
    """用于获取客服回复文本"""
    mode: ResponseMode = ResponseMode.STATIC  # 渲染模式，默认 static
    text: str | None = ""  # 待渲染回复文本
    prompt: str | None = ""  # rephrase 模式下的润色提示词

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResponseTemplate":
        return cls(
            mode=ResponseMode(data.get("mode", ResponseMode.STATIC)),
            text=data.get("text", ""),
            prompt=data.get("prompt", ""),
        )


@dataclass
class SlotValidation:
    """收集槽位步骤的校验配置"""
    condition: str | None = None  # 校验表达式，例如 slots.get('order_number')
    failure_template: ResponseTemplate | None = None  # 校验失败后的回复模板


@dataclass
class FlowStepLink:
    """节点跳转连接线"""
    target: str = ""  # 跳转目标步骤 ID

    @classmethod
    def build_links(cls, next_data: str | list[dict]) -> list["FlowStepLink"]:
        """根据 next 配置（字符串或列表）构造连接线列表"""
        if isinstance(next_data, str):
            # 字符串：固定跳转
            return [StaticLink(target=next_data)]
        links: list[FlowStepLink] = []
        for link_dict in next_data:
            if "if" in link_dict:
                # 条件跳转
                links.append(ConditionLink(condition=link_dict.get("if"), target=link_dict.get("then")))
            else:
                # 兜底跳转
                links.append(FallbackLink(target=link_dict.get("else")))
        return links


@dataclass
class StaticLink(FlowStepLink):
    """固定跳转连接线，例如 next: ask_order_number"""
    pass


@dataclass
class ConditionLink(FlowStepLink):
    """条件跳转连接线，满足 if 条件才跳转"""
    condition: str = ""


@dataclass
class FallbackLink(FlowStepLink):
    """兜底跳转连接线，前面条件都不满足时跳转"""
    pass


class FlowStepType(Enum):
    """步骤/节点类型"""
    START = "start"
    ACTION = "action"
    RESPONSE = "response"
    COLLECT = "collect"
    END = "end"


@dataclass
class FlowStep:
    """流程内步骤父类，包含五种步骤类型的公共属性"""
    id: str  # 步骤 ID
    type: FlowStepType  # 步骤类型
    next: list[FlowStepLink] = field(default_factory=list)  # 连接线，决定下一个步骤

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "FlowStep":
        """根据步骤字典中的 type 构造对应子类步骤对象"""
        clz = STEP_TYPE_TO_CLASS.get(step_data.get("type"))
        return clz.from_dict(step_data)

    @classmethod
    def base_fields(cls, step_data: dict[str, Any]) -> dict[str, Any]:
        """统一处理所有子类共有的 id / type / next 属性"""
        return {
            "id": step_data.get("id"),
            "type": step_data.get("type"),
            "next": FlowStepLink.build_links(step_data.get("next")),
        }


@dataclass
class StartFlowStep(FlowStep):
    """开始步骤，仅作任务开始标识"""

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "StartFlowStep":
        return cls(**FlowStep.base_fields(step_data))


@dataclass
class ActionFlowStep(FlowStep):
    """调用业务动作步骤；args 用于系统流程（如 action_response 的 mode/text/prompt）"""
    action: str = ""  # 动作名称，与 Action.name 一致
    args: Any = None  # 动作附加参数（系统流程使用）

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "ActionFlowStep":
        return cls(
            **FlowStep.base_fields(step_data),
            action=step_data.get("action"),
            args=step_data.get("args"),
        )


@dataclass
class CollectSlotStep(FlowStep):
    """收集槽位步骤"""
    slot_name: str = ""  # 需要收集的槽位名称
    template: ResponseTemplate = field(default_factory=ResponseTemplate)  # 追问模板
    validation: SlotValidation | None = None  # 收集到槽位后的校验（可选）

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "CollectSlotStep":
        validation = None
        if "validation" in step_data:
            validation = SlotValidation(
                condition=step_data["validation"].get("condition"),
                failure_template=ResponseTemplate.from_dict(step_data["validation"].get("failure_template")),
            )
        return cls(
            **FlowStep.base_fields(step_data),
            slot_name=step_data.get("slot_name"),
            template=ResponseTemplate.from_dict(step_data.get("template")),
            validation=validation,
        )


@dataclass
class ResponseFlowStep(FlowStep):
    """生成客服回复步骤"""
    template: ResponseTemplate = field(default_factory=ResponseTemplate)

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "ResponseFlowStep":
        return cls(
            **FlowStep.base_fields(step_data),
            template=ResponseTemplate.from_dict(step_data.get("template")),
        )


@dataclass
class EndFlowStep(FlowStep):
    """结束步骤，表示流程结束"""

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "EndFlowStep":
        return cls(**FlowStep.base_fields(step_data))


# 步骤类型名称与步骤类的映射
STEP_TYPE_TO_CLASS = {
    "start": StartFlowStep,
    "action": ActionFlowStep,
    "response": ResponseFlowStep,
    "collect": CollectSlotStep,
    "end": EndFlowStep,
}


@dataclass
class FlowSlot:
    """槽位信息"""
    name: str = ""  # 槽位名称
    type: str = "any"  # 槽位类型
    label: str = ""  # 槽位展示名称
    description: str = ""  # 槽位说明


@dataclass
class Flow:
    """流程定义"""
    id: str  # 流程 ID
    description: str = ""  # 流程描述
    steps: list[FlowStep] = field(default_factory=list)  # 步骤列表
    slots: list[FlowSlot] = field(default_factory=list)  # 流程用到的槽位列表
    name: str | None = None  # 流程名称

    def get_start_step(self) -> StartFlowStep | None:
        """获取流程内起始步骤"""
        for step in self.steps:
            if isinstance(step, StartFlowStep):
                return step
        return None

    def get_step(self, step_id: str) -> FlowStep | None:
        """根据步骤 ID 查询步骤对象"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None


@dataclass
class FlowCatalog:
    """流程定义清单，提供按流程 ID 查询流程的能力"""
    flows: dict[str, Flow] = field(default_factory=dict)  # key=流程 ID，value=Flow 对象
    slots: dict[str, FlowSlot] = field(default_factory=dict)  # key=槽位名称，value=FlowSlot 对象

    def get_flow(self, flow_id: str) -> Flow | None:
        """根据流程 ID 获取流程配置"""
        return self.flows.get(flow_id)
