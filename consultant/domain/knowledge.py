"""知识检索领域模型。

知识检索方向（knowledge 轨道）用于回答"信息、规则、政策"类咨询，例如课程信息、
退费政策、报名考试政策等。每个知识意图（KnowledgeIntent）关联若干信息提供者
（provider_ids），由知识处理器（KnowledgeHandler）并发调用这些提供者检索内容。
"""
from dataclasses import dataclass, field


@dataclass
class KnowledgeChunk:
    """信息检索后得到的内容片段"""
    content: str


@dataclass
class KnowledgeIntent:
    """知识意图，供 Planning 模块理解其含义"""
    id: str  # 意图唯一标识，例如 course_info
    description: str  # 意图自然语言说明
    provider_ids: list = field(default_factory=list)  # 处理该意图需要访问的 Provider ID 列表
    requires_object: str | None = None  # 是否要求焦点对象（course / order）


# 法硕培训场景的知识意图配置
# 说明：每个意图关联独立的 provider_id，避免多个意图共用一个 provider 导致答非所问。
#   faq.refund_policy  / faq.exam_policy / faq.class_arrangement 由 FAQProvider 按关键词检索；
#   rag.default 作为兜底检索，只在 FAQ 未命中时返回。
KNOWLEDGE_INTENTS: dict[str, KnowledgeIntent] = {
    "course_info": KnowledgeIntent(
        id="course_info",
        description="课程信息咨询（课程内容、适用人群、班次、价格）",
        provider_ids=["api.course"],
        requires_object="course",
    ),
    "order_info": KnowledgeIntent(
        id="order_info",
        description="订单信息咨询（报名缴费、订单状态）",
        provider_ids=["api.order"],
        requires_object="order",
    ),
    "refund_policy": KnowledgeIntent(
        id="refund_policy",
        description="退费政策咨询",
        provider_ids=["faq.refund_policy", "rag.default"],
    ),
    "exam_policy": KnowledgeIntent(
        id="exam_policy",
        description="考试报名与招生政策咨询",
        provider_ids=["faq.exam_policy", "rag.default"],
    ),
    "class_arrangement": KnowledgeIntent(
        id="class_arrangement",
        description="班次与上课安排咨询",
        provider_ids=["faq.class_arrangement", "rag.default"],
    ),
    "general_course_info": KnowledgeIntent(
        id="general_course_info",
        description="法硕培训通用信息咨询",
        provider_ids=["faq.general", "rag.default"],
    ),
}
