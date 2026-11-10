"""流程加载器。

读取 yaml 流程定义文件，解析出流程清单（FlowCatalog），包括所有流程与槽位。
"""
from pathlib import Path
from typing import Any

import yaml

from consultant.domain.flow_catalog import (
    FlowCatalog, Flow, FlowSlot, FlowStep, CollectSlotStep,
)


class FlowLoader:

    def load_many(self, flow_paths: list[Path]) -> FlowCatalog:
        """加载多个流程定义文件，合并为一份流程清单"""
        slots: dict[str, FlowSlot] = {}
        flows: dict[str, Flow] = {}
        for flow_path in flow_paths:
            catalog: FlowCatalog = self.load(flow_path)
            slots.update(catalog.slots)
            flows.update(catalog.flows)
        return FlowCatalog(flows=flows, slots=slots)

    def load(self, flow_path: Path) -> FlowCatalog:
        """读取单个流程定义 yaml 文件，得到流程与槽位"""
        # 1. 读取 yaml 内容
        with open(flow_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        # 2. 解析槽位配置
        slots = self._load_slots(data.get("slots", {}))
        # 3. 解析流程配置
        flows = self._load_flows(data.get("flows", {}), slots)
        return FlowCatalog(flows=flows, slots=slots)

    def _load_slots(self, slots_data: dict[str, Any]) -> dict[str, FlowSlot]:
        """解析槽位字典，封装为 FlowSlot 对象"""
        slots: dict[str, FlowSlot] = {}
        for slot_name, slot_data in slots_data.items():
            slots[slot_name] = FlowSlot(**slot_data, name=slot_name)
        return slots

    def _load_flows(self, flows_data: dict[str, Any], slots: dict[str, FlowSlot]) -> dict[str, Flow]:
        """解析所有流程定义"""
        flows: dict[str, Flow] = {}
        for flow_id, flow_data in flows_data.items():
            flows[flow_id] = self._load_flow(flow_id, flow_data, slots)
        return flows

    def _load_flow(self, flow_id: str, flow_data: dict[str, Any], slots: dict[str, FlowSlot]) -> Flow:
        """封装单个流程配置对象"""
        # 1. 解析流程内所有步骤
        steps: list[FlowStep] = [FlowStep.from_dict(d) for d in flow_data.get("steps", [])]
        # 2. 提取 collect 步骤用到的槽位
        step_slots = [slots.get(step.slot_name) for step in steps if isinstance(step, CollectSlotStep)]
        # 3. 封装 Flow 对象
        return Flow(
            id=flow_id,
            description=flow_data.get("description"),
            name=flow_data.get("name"),
            steps=steps,
            slots=step_slots,
        )
