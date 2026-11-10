"""法硕培训业务数据表 ORM 模型。

为支撑课程咨询、班次安排、授课老师、价格（专硕/学硕 × 线上/线下）、
线下地区、考试安排等检索场景，设计以下业务表：

1. courses            课程（科目维度：法硕专硕/学硕、民商法、刑法等）
2. class_schedules    班次（春秋季、上课时间、授课老师、线上线下、地区）
3. teachers           授课老师
4. course_prices      课程价格（专硕/学硕 × 线上/线下 的价位）
5. offline_locations  线下授课地区/教学点
6. exam_schedules     考试安排（模拟考、月考、模考等）
7. orders             报名订单（主表）
8. order_items        订单明细（订单对应的课程/班次）

这些表与 dialogue_states 表并存，供知识检索 Provider 与业务 Action 查询。
"""
from sqlalchemy import String, Integer, ForeignKey, Text, Date, Time, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from consultant.models.base import Base


class Course(Base):
    """课程（科目维度）"""
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)          # 课程ID，如 C001
    name: Mapped[str] = mapped_column(String(255), nullable=False)         # 课程名称
    category: Mapped[str] = mapped_column(String(64), nullable=False)      # 类别：专硕/学硕
    subject: Mapped[str] = mapped_column(String(128), nullable=False)      # 科目：法学综合/民商法/刑法等
    description: Mapped[str | None] = mapped_column(Text, nullable=True)   # 课程简介
    suitable_for: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 适用人群


class Teacher(Base):
    """授课老师"""
    __tablename__ = "teachers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)          # 老师ID
    name: Mapped[str] = mapped_column(String(64), nullable=False)          # 姓名
    title: Mapped[str | None] = mapped_column(String(128), nullable=True)  # 职称/头衔
    specialty: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 擅长科目


class ClassSchedule(Base):
    """班次（春秋季、上课时间、授课老师、线上线下、地区）"""
    __tablename__ = "class_schedules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)          # 班次ID
    course_id: Mapped[str] = mapped_column(String(64), ForeignKey("courses.id"), nullable=False)
    season: Mapped[str] = mapped_column(String(32), nullable=False)        # 季节：春季/秋季/全年
    class_name: Mapped[str] = mapped_column(String(255), nullable=False)   # 班次名称，如"民商法第5期强化班"
    teacher_id: Mapped[str] = mapped_column(String(64), ForeignKey("teachers.id"), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)          # 授课方式：线上/线下/混合
    schedule_time: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 上课时间描述，如"每周二四六 19:30-21:30"
    location_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("offline_locations.id"), nullable=True)  # 线下地区（线上可为空）
    start_date: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 开课日期
    status: Mapped[str] = mapped_column(String(32), default="招生中")       # 招生状态：招生中/已满/未开班


class CoursePrice(Base):
    """课程价格（专硕/学硕 × 线上/线下）"""
    __tablename__ = "course_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[str] = mapped_column(String(64), ForeignKey("courses.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)      # 专硕/学硕
    mode: Mapped[str] = mapped_column(String(32), nullable=False)          # 线上/线下
    price: Mapped[float] = mapped_column(nullable=False)                   # 价格（元）
    discount_note: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 优惠说明，如"老学员9折"


class OfflineLocation(Base):
    """线下授课地区/教学点"""
    __tablename__ = "offline_locations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)          # 地区ID
    name: Mapped[str] = mapped_column(String(255), nullable=False)         # 地区/教学点名称
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 详细地址


class ExamSchedule(Base):
    """考试安排（模拟考/月考/模考）"""
    __tablename__ = "exam_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)         # 考试名称，如"9月第一次月考"
    exam_type: Mapped[str] = mapped_column(String(64), nullable=False)     # 类型：月考/模拟考/阶段测试/模考
    exam_date: Mapped[str] = mapped_column(String(32), nullable=False)     # 考试日期
    subject_scope: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 考查范围
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True) # 备注


class Order(Base):
    """报名订单（主表）"""
    __tablename__ = "orders"

    order_number: Mapped[str] = mapped_column(String(64), primary_key=True)  # 订单号，如 A1001
    student_id: Mapped[str] = mapped_column(String(64), nullable=False)      # 学员编号
    status: Mapped[str] = mapped_column(String(32), nullable=False)          # 订单状态：待支付/已支付/已取消/已退款
    amount: Mapped[float] = mapped_column(nullable=False)                    # 订单金额（元）
    paid_at: Mapped[str | None] = mapped_column(String(32), nullable=True)   # 支付时间
    created_at: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 下单时间


class OrderItem(Base):
    """订单明细（一个订单可含多个课程）"""
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_number: Mapped[str] = mapped_column(String(64), ForeignKey("orders.order_number"), nullable=False)
    course_id: Mapped[str] = mapped_column(String(64), ForeignKey("courses.id"), nullable=False)  # 报名课程
    class_schedule_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("class_schedules.id"), nullable=True)  # 所选班次
