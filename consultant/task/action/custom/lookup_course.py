"""查询课程信息 Action。

对应 user_flows.yml 中 action_lookup_course 动作，从 courses 表真实查询课程信息，
并回填 course_summary 槽位。
"""
from sqlalchemy import select

from consultant.clients import database
from consultant.domain.action import ActionResult, Action
from consultant.domain.state import DialogueState
from consultant.models.business import Course


class LookupCourseAction(Action):
    name = "action_lookup_course"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = state.task_state.active_task.slots
        course_name = slots.get("course_name")
        course_id = slots.get("course_id")

        async with database.session_factory() as session:
            # 优先按 course_id 精确匹配，否则按名称模糊匹配
            if course_id:
                row = (await session.execute(
                    select(Course).where(Course.id == course_id)
                )).scalar_one_or_none()
            elif course_name:
                row = (await session.execute(
                    select(Course).where(Course.name.contains(course_name.strip()))
                )).scalars().first()
            else:
                row = None

        if row is None:
            summary = (
                f"没有查到「{course_name or course_id or '该课程'}」的信息。"
                "你可以换个课程名（如「法学硕士全程班」「民商法专项班」）再问，或回复「转人工」。"
            )
        else:
            summary = (
                f"「{row.name}」属于{row.category}·{row.subject}方向，"
                f"适合{row.suitable_for or '法硕备考学员'}。{row.description or ''}"
            )

        return ActionResult(slot_updates={"course_summary": summary})
