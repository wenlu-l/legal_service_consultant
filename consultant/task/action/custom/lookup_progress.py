"""查询学习进度 Action。

对应 user_flows.yml 中 action_lookup_progress 动作，从 class_schedules 表查询
班次信息（授课老师、上课时间、授课方式），并结合演示的学习进度数据回填
progress_summary 槽位。
"""
from sqlalchemy import select

from consultant.clients import database
from consultant.domain.action import ActionResult, Action
from consultant.domain.state import DialogueState
from consultant.models.business import ClassSchedule, Teacher


class LookupProgressAction(Action):
    name = "action_lookup_progress"

    async def run(self, state: DialogueState) -> ActionResult:
        class_name = state.task_state.active_task.slots.get("class_name")

        # 查班次真实信息（联表老师）
        schedule_info = ""
        async with database.session_factory() as session:
            if class_name:
                row = (await session.execute(
                    select(ClassSchedule, Teacher)
                    .join(Teacher, ClassSchedule.teacher_id == Teacher.id)
                    .where(ClassSchedule.class_name.contains(class_name.strip()))
                )).first()
                if row:
                    schedule, teacher = row
                    schedule_info = (
                        f"班次「{schedule.class_name}」：{schedule.season}班，"
                        f"{schedule.mode}授课，上课时间 {schedule.schedule_time}，"
                        f"授课老师 {teacher.name}。"
                    )

        # 学习进度（演示数据，后续接学习记录表）
        progress = (
            "已上 12/32 次课，视频完成 78%，作业提交 15/20，最近模考 112 分。"
        )
        summary = (schedule_info + " " if schedule_info else "") + "学习进度：" + progress
        return ActionResult(slot_updates={"progress_summary": summary})
