"""提交售后工单 Action。

对应 user_flows.yml 中 action_submit_ticket 动作，创建工单并回填
ticket_number / ticket_expectation 槽位。当前返回演示数据。
"""
import uuid

from consultant.domain.action import ActionResult, Action
from consultant.domain.state import DialogueState


class SubmitTicketAction(Action):
    name = "action_submit_ticket"

    async def run(self, state: DialogueState) -> ActionResult:
        # TODO: 接入真实后端后，改为调用工单创建接口
        ticket_number = "TK" + uuid.uuid4().hex[:8].upper()
        return ActionResult(slot_updates={
            "ticket_number": ticket_number,
            "ticket_expectation": "客服会在 24 小时内与您联系，请保持电话畅通。",
        })
