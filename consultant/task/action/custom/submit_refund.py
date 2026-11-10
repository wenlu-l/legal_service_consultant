"""提交退款申请 Action。

对应 user_flows.yml 中 action_submit_refund 动作，创建退款申请并回填
refund_result 槽位。当前返回演示数据。
"""
from consultant.domain.action import ActionResult, Action
from consultant.domain.state import DialogueState


class SubmitRefundAction(Action):
    name = "action_submit_refund"

    async def run(self, state: DialogueState) -> ActionResult:
        # TODO: 接入真实后端后，改为调用退款申请接口
        return ActionResult(slot_updates={
            "refund_result": "我们已受理，预计 3-5 个工作日原路退回，请留意短信通知。"
        })
