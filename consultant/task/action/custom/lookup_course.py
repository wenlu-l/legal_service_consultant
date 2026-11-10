"""查询课程信息 Action。

对应 user_flows.yml 中 action_lookup_course 动作，查询课程信息并回填 course_summary 槽位。
当前返回演示数据，后续可改为调用真实后端接口。
"""
from consultant.domain.action import ActionResult, Action
from consultant.domain.state import DialogueState


class LookupCourseAction(Action):
    name = "action_lookup_course"

    async def run(self, state: DialogueState) -> ActionResult:
        # TODO: 接入真实后端后，改为调用课程查询接口
        slots = state.task_state.active_task.slots
        course_name = slots.get("course_name") or slots.get("course_id") or "该课程"
        course_summary = (
            f"「{course_name}」是法硕考研核心课程，覆盖考纲重点与真题讲解，"
            "配套讲义、刷题与答疑服务，适合备考阶段系统复习。"
        )
        return ActionResult(slot_updates={"course_summary": course_summary})
