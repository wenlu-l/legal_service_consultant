"""查询订单信息 Action。

对应 user_flows.yml 中 action_lookup_order 动作，从 orders + order_items 表
真实查询订单状态与报名课程，回填 order_status / order_summary 槽位。
"""
from sqlalchemy import select

from consultant.clients import database
from consultant.domain.action import ActionResult, Action
from consultant.domain.state import DialogueState
from consultant.models.business import Order, OrderItem, Course


class LookupOrderAction(Action):
    name = "action_lookup_order"

    async def run(self, state: DialogueState) -> ActionResult:
        order_number = state.task_state.active_task.slots.get("order_number")

        async with database.session_factory() as session:
            row = (await session.execute(
                select(Order).where(Order.order_number == order_number)
            )).scalar_one_or_none()

            if row is None:
                return ActionResult(slot_updates={
                    "order_status": "未查到",
                    "order_summary": f"没有查到订单「{order_number}」，请核对订单号后重试。",
                })

            # 查订单明细（联课程名）
            items = (await session.execute(
                select(Course.name)
                .join(OrderItem, OrderItem.course_id == Course.id)
                .where(OrderItem.order_number == order_number)
            )).scalars().all()

        course_names = "、".join(items) if items else "（无课程明细）"
        return ActionResult(slot_updates={
            "order_status": row.status,
            "order_summary": (
                f"报名课程：{course_names}，金额：￥{row.amount:.0f}，"
                f"支付时间：{row.paid_at or '未支付'}"
            ),
        })
