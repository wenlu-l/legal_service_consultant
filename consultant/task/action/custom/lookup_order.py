"""查询订单信息 Action。

对应 user_flows.yml 中 action_lookup_order 动作，查询订单状态并回填
order_status / order_summary 槽位。当前返回演示数据。
"""
from consultant.domain.action import ActionResult, Action
from consultant.domain.state import DialogueState


class LookupOrderAction(Action):
    name = "action_lookup_order"

    async def run(self, state: DialogueState) -> ActionResult:
        # TODO: 接入真实后端后，改为调用订单查询接口
        order_number = state.task_state.active_task.slots.get("order_number")
        return ActionResult(slot_updates={
            "order_status": "已支付",
            "order_summary": "报名课程：民商法全程班，金额：￥9800，支付时间：2026-11-01",
        })
