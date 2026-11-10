"""查询学习进度 Action。

对应 user_flows.yml 中 action_lookup_progress 动作，查询学习进度并回填
progress_summary 槽位。当前返回演示数据。
"""
from consultant.domain.action import ActionResult, Action
from consultant.domain.state import DialogueState


class LookupProgressAction(Action):
    name = "action_lookup_progress"

    async def run(self, state: DialogueState) -> ActionResult:
        # TODO: 接入真实后端后，改为调用学习数据查询接口
        class_name = state.task_state.active_task.slots.get("class_name") or "当前班次"
        progress_summary = (
            f"{class_name}：已上 12/32 次课，视频完成 78%，作业提交 15/20，最近模考 112 分。"
        )
        return ActionResult(slot_updates={"progress_summary": progress_summary})
