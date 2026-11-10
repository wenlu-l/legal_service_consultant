"""法硕培训业务数据种子脚本。

用法（先确保 MySQL 已启动）：
    python seed_data.py

作用：向 courses / teachers / class_schedules / course_prices /
      offline_locations / exam_schedules / orders / order_items 八张表插入演示数据，
      供知识检索 Provider 与业务 Action 查询。
"""
import asyncio

from sqlalchemy import select, func

from consultant.clients import database
from consultant.models.business import (
    Course, Teacher, ClassSchedule, CoursePrice, OfflineLocation, ExamSchedule,
    Order, OrderItem,
)


# ---------------------------------------------------------------------------
# 演示数据
# ---------------------------------------------------------------------------

COURSES = [
    {"id": "C001", "name": "法学硕士（非法学）全程班", "category": "专硕", "subject": "法学综合",
     "description": "法硕（非法学）零基础全程班，覆盖刑法、民法、法理、宪法、法制史五大科目。",
     "suitable_for": "非法学本科、零基础跨考学员"},
    {"id": "C002", "name": "法学硕士（法学）全程班", "category": "学硕", "subject": "法学综合",
     "description": "法硕（法学）强化班，面向法学本科，聚焦专业深度与真题。",
     "suitable_for": "法学本科、有基础学员"},
    {"id": "C003", "name": "民商法方向专项班", "category": "专硕", "subject": "民商法",
     "description": "民商法方向专项提升，民法+商法精讲与刷题。",
     "suitable_for": "目标民商法方向的学员"},
    {"id": "C004", "name": "刑法方向专项班", "category": "专硕", "subject": "刑法",
     "description": "刑法方向专项提升，刑法总则分则精讲。",
     "suitable_for": "目标刑法方向的学员"},
    {"id": "C005", "name": "主观题冲刺班", "category": "专硕", "subject": "主观题",
     "description": "主观题专项，案例分析与论述题突破。",
     "suitable_for": "通过客观题、备考主观题的学员"},
]

TEACHERS = [
    {"id": "T001", "name": "张明", "title": "法学博士、主讲民法", "specialty": "民法、商法"},
    {"id": "T002", "name": "李华", "title": "刑法学博士", "specialty": "刑法"},
    {"id": "T003", "name": "王芳", "title": "法学理论博士、主讲法理", "specialty": "法理学、宪法"},
    {"id": "T004", "name": "陈志强", "title": "法制史方向名师", "specialty": "法制史"},
    {"id": "T005", "name": "刘洋", "title": "主观题教研组长", "specialty": "主观题、案例分析"},
]

LOCATIONS = [
    {"id": "L001", "name": "北京海淀教学点", "address": "北京市海淀区中关村大街 1 号"},
    {"id": "L002", "name": "上海徐汇教学点", "address": "上海市徐汇区漕溪北路 88 号"},
    {"id": "L003", "name": "广州天河教学点", "address": "广州市天河区体育西路 191 号"},
    {"id": "L004", "name": "武汉武昌教学点", "address": "武汉市武昌区中南路 99 号"},
    {"id": "L005", "name": "深圳福田教学点", "address": "深圳市福田区深南大道 2008 号"},
    {"id": "L006", "name": "成都武侯教学点", "address": "成都市武侯区人民南路四段 30 号"},
    {"id": "L007", "name": "杭州西湖教学点", "address": "杭州市西湖区文三路 478 号"},
]

CLASS_SCHEDULES = [
    # —— 线上班 ——
    {"id": "S001", "course_id": "C001", "season": "春季", "class_name": "法硕专硕春季线上班",
     "teacher_id": "T001", "mode": "线上", "schedule_time": "每周二、四、六 19:30-21:30",
     "location_id": None, "start_date": "2026-03-01", "status": "招生中"},
    {"id": "S004", "course_id": "C003", "season": "秋季", "class_name": "民商法方向第5期线上班",
     "teacher_id": "T001", "mode": "线上", "schedule_time": "每周一、三 20:00-22:00",
     "location_id": None, "start_date": "2026-09-10", "status": "招生中"},
    {"id": "S006", "course_id": "C005", "season": "秋季", "class_name": "主观题冲刺线上班",
     "teacher_id": "T005", "mode": "线上", "schedule_time": "每周五 19:30-21:30",
     "location_id": None, "start_date": "2026-10-15", "status": "招生中"},

    # —— 北京线下班 ——
    {"id": "S101", "course_id": "C001", "season": "秋季", "class_name": "法硕专硕北京线下班",
     "teacher_id": "T003", "mode": "线下", "schedule_time": "每周六、日 9:00-17:00",
     "location_id": "L001", "start_date": "2026-09-05", "status": "招生中"},
    {"id": "S102", "course_id": "C002", "season": "春季", "class_name": "法硕学硕北京线下班",
     "teacher_id": "T002", "mode": "线下", "schedule_time": "每周六 9:00-17:00",
     "location_id": "L001", "start_date": "2026-03-08", "status": "招生中"},

    # —— 上海线下班 ——
    {"id": "S201", "course_id": "C001", "season": "秋季", "class_name": "法硕专硕上海线下班",
     "teacher_id": "T001", "mode": "线下", "schedule_time": "每周六、日 9:00-17:00",
     "location_id": "L002", "start_date": "2026-09-12", "status": "招生中"},
    {"id": "S202", "course_id": "C003", "season": "春季", "class_name": "民商法上海线下班",
     "teacher_id": "T001", "mode": "线下", "schedule_time": "每周日 9:00-17:00",
     "location_id": "L002", "start_date": "2026-03-15", "status": "招生中"},

    # —— 广州线下班 ——
    {"id": "S301", "course_id": "C004", "season": "全年", "class_name": "刑法方向广州线下班",
     "teacher_id": "T002", "mode": "线下", "schedule_time": "每周日 9:00-17:00",
     "location_id": "L003", "start_date": "2026-02-15", "status": "已满"},
    {"id": "S302", "course_id": "C001", "season": "秋季", "class_name": "法硕专硕广州线下班",
     "teacher_id": "T004", "mode": "线下", "schedule_time": "每周六、日 9:00-17:00",
     "location_id": "L003", "start_date": "2026-09-06", "status": "招生中"},

    # —— 武汉线下班 ——
    {"id": "S401", "course_id": "C001", "season": "秋季", "class_name": "法硕专硕武汉线下班",
     "teacher_id": "T003", "mode": "线下", "schedule_time": "每周六、日 9:00-17:00",
     "location_id": "L004", "start_date": "2026-09-05", "status": "招生中"},
    {"id": "S402", "course_id": "C002", "season": "春季", "class_name": "法硕学硕武汉线下班",
     "teacher_id": "T004", "mode": "线下", "schedule_time": "每周日 9:00-17:00",
     "location_id": "L004", "start_date": "2026-03-10", "status": "招生中"},
    {"id": "S403", "course_id": "C005", "season": "秋季", "class_name": "主观题武汉线下冲刺班",
     "teacher_id": "T005", "mode": "线下", "schedule_time": "每周六 9:00-17:00",
     "location_id": "L004", "start_date": "2026-10-20", "status": "招生中"},

    # —— 深圳线下班 ——
    {"id": "S501", "course_id": "C001", "season": "秋季", "class_name": "法硕专硕深圳线下班",
     "teacher_id": "T001", "mode": "线下", "schedule_time": "每周六、日 9:00-17:00",
     "location_id": "L005", "start_date": "2026-09-05", "status": "招生中"},
    {"id": "S502", "course_id": "C003", "season": "春季", "class_name": "民商法深圳线下班",
     "teacher_id": "T001", "mode": "线下", "schedule_time": "每周日 9:00-17:00",
     "location_id": "L005", "start_date": "2026-03-14", "status": "招生中"},

    # —— 成都线下班 ——
    {"id": "S601", "course_id": "C001", "season": "秋季", "class_name": "法硕专硕成都线下班",
     "teacher_id": "T002", "mode": "线下", "schedule_time": "每周六、日 9:00-17:00",
     "location_id": "L006", "start_date": "2026-09-07", "status": "招生中"},
    {"id": "S602", "course_id": "C004", "season": "春季", "class_name": "刑法方向成都线下班",
     "teacher_id": "T002", "mode": "线下", "schedule_time": "每周日 9:00-17:00",
     "location_id": "L006", "start_date": "2026-03-13", "status": "招生中"},

    # —— 杭州线下班 ——
    {"id": "S701", "course_id": "C001", "season": "秋季", "class_name": "法硕专硕杭州线下班",
     "teacher_id": "T003", "mode": "线下", "schedule_time": "每周六、日 9:00-17:00",
     "location_id": "L007", "start_date": "2026-09-06", "status": "招生中"},
    {"id": "S702", "course_id": "C002", "season": "秋季", "class_name": "法硕学硕杭州线下班",
     "teacher_id": "T004", "mode": "线下", "schedule_time": "每周日 9:00-17:00",
     "location_id": "L007", "start_date": "2026-09-08", "status": "招生中"},
]

COURSE_PRICES = [
    # 专硕 × 线上/线下
    {"course_id": "C001", "category": "专硕", "mode": "线上", "price": 9800, "discount_note": "老学员9折"},
    {"course_id": "C001", "category": "专硕", "mode": "线下", "price": 15800, "discount_note": "老学员9折"},
    # 学硕 × 线上/线下
    {"course_id": "C002", "category": "学硕", "mode": "线上", "price": 11800, "discount_note": "老学员9折"},
    {"course_id": "C002", "category": "学硕", "mode": "线下", "price": 17800, "discount_note": "老学员9折"},
    # 专项班
    {"course_id": "C003", "category": "专硕", "mode": "线上", "price": 6800, "discount_note": None},
    {"course_id": "C003", "category": "专硕", "mode": "线下", "price": 10800, "discount_note": None},
    {"course_id": "C004", "category": "专硕", "mode": "线上", "price": 6800, "discount_note": None},
    {"course_id": "C004", "category": "专硕", "mode": "线下", "price": 10800, "discount_note": None},
    # 主观题
    {"course_id": "C005", "category": "专硕", "mode": "线上", "price": 4980, "discount_note": "老学员9折"},
]

EXAM_SCHEDULES = [
    {"name": "3月入学摸底测试", "exam_type": "阶段测试", "exam_date": "2026-03-15",
     "subject_scope": "法学综合（客观题）", "remark": "线上进行"},
    {"name": "5月第一次月考", "exam_type": "月考", "exam_date": "2026-05-10",
     "subject_scope": "刑法+民法", "remark": "线上进行"},
    {"name": "7月第二次月考", "exam_type": "月考", "exam_date": "2026-07-12",
     "subject_scope": "法理+宪法+法制史", "remark": "线上进行"},
    {"name": "9月全真模拟考", "exam_type": "模拟考", "exam_date": "2026-09-20",
     "subject_scope": "法学综合（全真）", "remark": "线下各教学点同步"},
    {"name": "11月主观题模考", "exam_type": "模考", "exam_date": "2026-11-15",
     "subject_scope": "主观题（案例+论述）", "remark": "线上进行"},
]

ORDERS = [
    {"order_number": "A1001", "student_id": "stu001", "status": "已支付",
     "amount": 9800.0, "paid_at": "2026-03-02 10:20:00", "created_at": "2026-03-01 09:00:00"},
    {"order_number": "A1002", "student_id": "stu002", "status": "已支付",
     "amount": 15800.0, "paid_at": "2026-09-01 14:00:00", "created_at": "2026-08-30 20:30:00"},
    {"order_number": "A1003", "student_id": "stu003", "status": "待支付",
     "amount": 6800.0, "paid_at": None, "created_at": "2026-11-09 11:00:00"},
    {"order_number": "A1004", "student_id": "stu001", "status": "已退款",
     "amount": 4980.0, "paid_at": "2026-10-16 09:00:00", "created_at": "2026-10-15 15:00:00"},
]

ORDER_ITEMS = [
    {"order_number": "A1001", "course_id": "C001", "class_schedule_id": "S001"},   # 专硕春季线上班
    {"order_number": "A1002", "course_id": "C001", "class_schedule_id": "S401"},   # 专硕武汉线下班
    {"order_number": "A1003", "course_id": "C003", "class_schedule_id": "S004"},   # 民商法线上班
    {"order_number": "A1004", "course_id": "C005", "class_schedule_id": "S006"},   # 主观题线上班
]


async def seed():
    database.init_db_engine()
    await database.create_tables()

    async with database.session_factory() as session:
        # 统计现有数据，避免重复插入
        existing = (await session.execute(select(func.count()).select_from(Course))).scalar()
        if existing and existing > 0:
            print(f"courses 表已有 {existing} 条数据，跳过种子插入（如需重灌请先清空）。")
            return

        # 先插入无外键依赖的父表，flush 后再插子表，避免外键约束顺序问题
        session.add_all([Course(**c) for c in COURSES])
        session.add_all([Teacher(**t) for t in TEACHERS])
        session.add_all([OfflineLocation(**l) for l in LOCATIONS])
        session.add_all([ExamSchedule(**e) for e in EXAM_SCHEDULES])
        await session.flush()

        session.add_all([ClassSchedule(**s) for s in CLASS_SCHEDULES])
        session.add_all([CoursePrice(**p) for p in COURSE_PRICES])
        await session.flush()

        session.add_all([Order(**o) for o in ORDERS])
        await session.flush()

        session.add_all([OrderItem(**i) for i in ORDER_ITEMS])
        await session.commit()

        print("种子数据插入完成：")
        for model in [Course, Teacher, OfflineLocation, ClassSchedule, CoursePrice,
                      ExamSchedule, Order, OrderItem]:
            cnt = (await session.execute(select(func.count()).select_from(model))).scalar()
            print(f"  {model.__tablename__}: {cnt} 条")

    await database.close_db_engine()


if __name__ == "__main__":
    asyncio.run(seed())
