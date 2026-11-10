"""知识信息提供者。

每个 Provider 负责从某个数据源检索内容，返回 KnowledgeChunk 列表：
- CourseAPIProvider：查询课程信息（需课程卡片）；
- OrderAPIProvider：查询订单信息（需订单卡片）；
- FAQProvider：按 provider_id 检索对应主题的 FAQ 条目（关键词匹配）；
- RAGProvider：兜底检索（当前用关键词粗检索，后续可替换为向量检索）。

FAQ 数据源集中在 FAQ_DB，按 provider_id 分组，便于维护。
"""
import json
from abc import ABC, abstractmethod

from consultant.domain.knowledge import KnowledgeChunk
from consultant.domain.messages import UserMessage
from consultant.domain.state import DialogueState


class KnowledgeProvider(ABC):
    """各种信息提供者父类"""
    provider_id: str  # 信息提供者唯一标识

    @abstractmethod
    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        """信息检索抽象方法"""
        pass


class CourseAPIProvider(KnowledgeProvider):
    provider_id = "api.course"

    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        # TODO: 接入真实后端后，改为调用课程查询接口
        course = state.shared_state.focused_object
        if course is None or course.type != "course":
            return []
        info = {
            "课程名称": course.title or course.id,
            "课程ID": course.id,
            "适用人群": "法硕考研备考学员",
            "班次": "民商法方向全程班",
            "价格": "9800 元",
        }
        text = json.dumps(info, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content="课程信息:\n" + text)]


class OrderAPIProvider(KnowledgeProvider):
    provider_id = "api.order"

    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        # TODO: 接入真实后端后，改为调用订单查询接口
        order = state.shared_state.focused_object
        if order is None or order.type != "order":
            return []
        info = {
            "订单号": order.id,
            "订单标题": order.title or "法硕课程报名",
            "状态": "已支付",
            "金额": "9800 元",
        }
        text = json.dumps(info, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content="订单信息:\n" + text)]


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
    """按 provider_id 检索对应主题的 FAQ 条目。

    通过 provider_id 定位到 FAQ_DB 的某一组条目，再用用户消息做关键词匹配，
    命中则返回对应答案；未命中返回空列表（交给 rag.default 兜底）。
    """

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
        # 该主题下无关键词命中，返回空，由 rag.default 兜底
        return []


class RAGProvider(KnowledgeProvider):
    """兜底检索。

    当前用「全库关键词粗检索」模拟，后续可替换为向量检索 / 语义检索。
    始终返回至少一条内容，避免用户每次都被迫转人工。
    """
    provider_id = "rag.default"

    async def retrieve(self, state: DialogueState, user_message: UserMessage) -> list[KnowledgeChunk]:
        query = (user_message.text or "").strip()

        # 全库关键词粗检索：扫所有 FAQ 条目，命中则返回最匹配的一条
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

        # 完全没命中，给出引导性兜底，而不是一句"未检索到"
        return [KnowledgeChunk(
            content="关于这个问题，我暂时没有检索到确切答案。你可以换一种说法再问一次，"
                    "或回复「转人工」由老师为你解答。"
        )]


def build_default_providers() -> list[KnowledgeProvider]:
    """返回系统支持的信息提供者实例列表"""
    providers: list[KnowledgeProvider] = [
        CourseAPIProvider(),
        OrderAPIProvider(),
    ]

    # 为每个 FAQ 主题创建一个带独立 provider_id 的实例
    for faq_id in FAQ_DB:
        p = FAQProvider()
        p.provider_id = faq_id
        providers.append(p)

    providers.append(RAGProvider())
    return providers
