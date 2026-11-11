"""知识信息提供者。

每个 Provider 负责从某个数据源检索内容，返回 KnowledgeChunk 列表：
- CourseAPIProvider：查询课程信息（需课程卡片）
- OrderAPIProvider：查询订单信息（需订单卡片）
- CourseScheduleProvider：查询班次/春秋季/上课时间/授课老师/线上线下/地区
- CoursePriceProvider：查询专硕/学硕 × 线上/线下 价格
- TeacherProvider：查询授课老师
- ExamProvider：查询考试安排
- FAQProvider：按 provider_id 检索对应主题的 FAQ 条目（关键词匹配）
- RAGProvider：兜底检索

业务数据（课程/班次/价格/老师/考试）从 MySQL 业务表真实查询；
FAQ 数据集中在 FAQ_DB，按 provider_id 分组。
"""
import json
from abc import ABC, abstractmethod

from sqlalchemy import select

from consultant.clients import database
from consultant.domain.knowledge import KnowledgeChunk
from consultant.domain.messages import UserMessage, MessageObject
from consultant.domain.state import DialogueState
from consultant.models.business import (
    Course, Teacher, ClassSchedule, CoursePrice, OfflineLocation, ExamSchedule,
    Order, OrderItem,
)


class KnowledgeProvider(ABC):
    """各种信息提供者父类"""
    provider_id: str  # 信息提供者唯一标识

    @abstractmethod
    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        """信息检索抽象方法"""
        pass


class CourseAPIProvider(KnowledgeProvider):
    """查询课程信息（从 courses 表真实查询）"""
    provider_id = "api.course"

    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        course = state.shared_state.focused_object
        if course is None or course.type != "course":
            return []
        async with database.session_factory() as session:
            row = (await session.execute(
                select(Course).where(Course.id == course.id)
            )).scalar_one_or_none()
        if row is None:
            return [KnowledgeChunk(content=f"没有查到课程「{course.title or course.id}」的信息，"
                                            "你可以换个课程名再问，或回复「转人工」。")]
        info = {
            "课程名称": row.name,
            "课程ID": row.id,
            "类别": row.category,
            "科目": row.subject,
            "适用人群": row.suitable_for,
            "简介": row.description,
        }
        return [KnowledgeChunk(content="课程信息:\n" + json.dumps(info, ensure_ascii=False, indent=2))]


class OrderAPIProvider(KnowledgeProvider):
    """查询订单信息（从 orders + order_items 联表真实查询）"""
    provider_id = "api.order"

    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        order = state.shared_state.focused_object
        if order is None or order.type != "order":
            return []
        async with database.session_factory() as session:
            row = (await session.execute(
                select(Order).where(Order.order_number == order.id)
            )).scalar_one_or_none()
            if row is None:
                return [KnowledgeChunk(content=f"没有查到订单「{order.id}」，你可以核对订单号后重试，"
                                                "或回复「转人工」。")]
            # 查订单明细（联课程名）
            items = (await session.execute(
                select(OrderItem, Course.name)
                .join(Course, OrderItem.course_id == Course.id)
                .where(OrderItem.order_number == order.id)
            )).all()

        info = {
            "订单号": row.order_number,
            "状态": row.status,
            "金额": f"{row.amount:.0f} 元",
            "支付时间": row.paid_at or "未支付",
            "报名课程": [name for _, name in items] or ["（无明细）"],
        }
        return [KnowledgeChunk(content="订单信息:\n" + json.dumps(info, ensure_ascii=False, indent=2))]


class CourseScheduleProvider(KnowledgeProvider):
    """查询班次/春秋季/上课时间/授课老师/线上线下/地区（联表查询，按课程与线上线下过滤）"""
    provider_id = "api.schedule"

    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        query = (user_message.text or "").strip()
        # 1. 解析用户想查的授课方式（线上 / 线下）
        mode_filter: str | None = None
        if "线下" in query:
            mode_filter = "线下"
        elif "线上" in query or "直播" in query or "网课" in query or "网课" in query:
            mode_filter = "线上"

        async with database.session_factory() as session:
            stmt = (
                select(ClassSchedule, Teacher, OfflineLocation, Course.name)
                .join(Teacher, ClassSchedule.teacher_id == Teacher.id)
                .outerjoin(OfflineLocation, ClassSchedule.location_id == OfflineLocation.id)
                .join(Course, ClassSchedule.course_id == Course.id)
            )
            # 2. 若存在课程焦点对象，按 course_id 过滤到具体课程
            focused = state.shared_state.focused_object
            if focused is not None and focused.type == "course":
                stmt = stmt.where(ClassSchedule.course_id == focused.id)
            # 3. 按授课方式过滤
            if mode_filter is not None:
                stmt = stmt.where(ClassSchedule.mode == mode_filter)

            rows = (await session.execute(stmt)).all()

        if not rows:
            # 给一个明确的"没查到"提示，避免 LLM 敷衍
            course_hint = ""
            focused = state.shared_state.focused_object
            if focused is not None and focused.type == "course":
                course_hint = f"「{focused.title or focused.id}」"
            mode_hint = mode_filter or "线上线下"
            return [KnowledgeChunk(
                content=f"没有查到{course_hint}的{mode_hint}班次安排。"
                        "请不要编造班次信息，直接如实告知用户目前没有查到，并引导用户换课程或转人工。"
            )]

        items = []
        for schedule, teacher, location, course_name in rows:
            items.append({
                "课程": course_name,
                "班次": schedule.class_name,
                "季节": schedule.season,
                "授课老师": teacher.name if teacher else "待定",
                "授课方式": schedule.mode,
                "上课时间": schedule.schedule_time,
                "线下地区": location.name if location else "线上",
                "开课日期": schedule.start_date,
                "状态": schedule.status,
            })
        return [KnowledgeChunk(content="班次安排:\n" + json.dumps(items, ensure_ascii=False, indent=2))]


class CoursePriceProvider(KnowledgeProvider):
    """查询专硕/学硕 × 线上/线下 价格"""
    provider_id = "api.price"
    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        async with database.session_factory() as session:
            rows = (await session.execute(
                select(CoursePrice, Course.name)
                .join(Course, CoursePrice.course_id == Course.id)
            )).all()

        if not rows:
            return [KnowledgeChunk(content="目前暂无课程价格信息。")]

        items = []
        for price, course_name in rows:
            items.append({
                "课程": course_name,
                "类型": price.category,
                "授课方式": price.mode,
                "价格": f"{price.price:.0f} 元",
                "优惠": price.discount_note or "无",
            })
        return [KnowledgeChunk(content="课程价格:\n" + json.dumps(items, ensure_ascii=False, indent=2))]


class TeacherProvider(KnowledgeProvider):
    """查询授课老师"""
    provider_id = "api.teacher"

    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        async with database.session_factory() as session:
            rows = (await session.execute(select(Teacher))).scalars().all()

        if not rows:
            return [KnowledgeChunk(content="目前暂无授课老师信息。")]

        items = [{"姓名": t.name, "头衔": t.title, "擅长": t.specialty} for t in rows]
        return [KnowledgeChunk(content="授课老师:\n" + json.dumps(items, ensure_ascii=False, indent=2))]


class ExamProvider(KnowledgeProvider):
    """查询考试安排"""
    provider_id = "api.exam"

    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        async with database.session_factory() as session:
            rows = (await session.execute(
                select(ExamSchedule).order_by(ExamSchedule.exam_date)
            )).scalars().all()

        if not rows:
            return [KnowledgeChunk(content="目前暂无考试安排信息。")]

        items = [{
            "考试": e.name,
            "类型": e.exam_type,
            "日期": e.exam_date,
            "范围": e.subject_scope,
            "备注": e.remark,
        } for e in rows]
        return [KnowledgeChunk(content="考试安排:\n" + json.dumps(items, ensure_ascii=False, indent=2))]


# ---------------------------------------------------------------------------
# FAQ 数据源：按 provider_id 分组，每个主题对应若干条 FAQ（问题关键词 → 答案）
# ---------------------------------------------------------------------------
FAQ_DB: dict[str, list[dict]] = {
    "faq.refund_policy": [
        {"keywords": ["退费", "退款", "退钱", "退课", "退班", "退费政策"],
         "answer": "退费政策：开课前可全额退款；开课后按已上课程比例扣除相应费用后，退还剩余部分。具体以报名协议为准。"},
    ],
    "faq.exam_policy": [
        {"keywords": ["考试", "报名", "招生", "报考", "国家线", "分数线", "招生政策", "考试政策"],
         "answer": "考试报名与招生政策：法硕（非法学）初试考思想政治理论、英语、法学专业基础、法学专业综合；报名一般在每年 10 月，初试在 12 月。具体以当年教育部和院校公告为准。"},
    ],
    "faq.class_arrangement": [
        {"keywords": ["班次", "上课", "安排", "课表", "开课", "直播", "时间", "课时", "上课安排"],
         "answer": "班次与上课安排：全程班分为基础、强化、冲刺三个阶段；每周二、四、六晚 19:30 直播授课，课后提供录播回放。具体班次安排请查看课程页或咨询老师。"},
    ],
    "faq.general": [
        {"keywords": ["试听", "随报随学", "讲义", "答疑", "服务", "辅导", "资料"],
         "answer": "培训服务说明：支持免费试听、随报随学；配套讲义、刷题题库、在线答疑与班主任督学服务。"},
    ],
}


class FAQProvider(KnowledgeProvider):
    """按 provider_id 检索对应主题的 FAQ 条目（关键词匹配）"""

    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        entries = FAQ_DB.get(self.provider_id, [])
        if not entries:
            return []
        query = (user_message.text or "").strip()
        if not query:
            return []
        for entry in entries:
            if any(kw in query for kw in entry["keywords"]):
                return [KnowledgeChunk(content=entry["answer"])]
        return []


class RAGProvider(KnowledgeProvider):
    """兜底检索（全库关键词粗检索，后续可替换为向量检索）"""
    provider_id = "rag.default"

    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        query = (user_message.text or "").strip()
        best: KnowledgeChunk | None = None
        best_score = 0
        for entries in FAQ_DB.values():
            for entry in entries:
                score = sum(1 for kw in entry["keywords"] if kw in query)
                if score > best_score:
                    best_score = score
                    best = KnowledgeChunk(content=entry["answer"])
        if best is not None:
            return [best]
        return [KnowledgeChunk(
            content="关于这个问题，我暂时没有检索到确切答案。你可以换一种说法再问一次，"
                    "或回复「转人工」由老师为你解答。"
        )]


class CourseRecommendProvider(KnowledgeProvider):
    """课程推荐：从 courses 表推荐课程，返回带卡片对象的回复。

    用户表达"帮我推荐课程 / 不知道该选哪个"等意图时，推荐招生中的课程，
    返回一个 KnowledgeChunk：content 为推荐理由文字，object 为课程卡片，
    由响应器渲染成「文字 + 卡片」的富消息回复。
    """
    provider_id = "api.recommend"

    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        async with database.session_factory() as session:
            rows = (await session.execute(
                select(Course).order_by(Course.id)
            )).scalars().all()

        if not rows:
            return [KnowledgeChunk(content="目前暂时没有可推荐的课程，你可以稍后再来，或回复「转人工」咨询老师。")]

        # 取第一门作为推荐课程（这里简单取排序后的第一门，后续可接入个性化推荐）
        course = rows[0]
        # 组装课程卡片对象
        card = MessageObject(
            type="course",
            id=course.id,
            title=course.name,
            attributes={"category": course.category, "subject": course.subject},
        )
        recommend_text = (
            f"为你推荐「{course.name}」：属于{course.category}·{course.subject}方向，"
            f"适合{course.suitable_for or '法硕备考学员'}。{course.description or ''}"
            "你可以点击下方卡片直接了解这门课程，也可以告诉我想了解班次或价格。"
        )
        return [KnowledgeChunk(content=recommend_text, object=card)]


def build_default_providers() -> list[KnowledgeProvider]:
    """返回系统支持的信息提供者实例列表"""
    providers: list[KnowledgeProvider] = [
        CourseAPIProvider(),
        OrderAPIProvider(),
        CourseScheduleProvider(),
        CoursePriceProvider(),
        TeacherProvider(),
        ExamProvider(),
        CourseRecommendProvider(),
    ]
    for faq_id in FAQ_DB:
        p = FAQProvider()
        p.provider_id = faq_id
        providers.append(p)
    providers.append(RAGProvider())
    return providers
