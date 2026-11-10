"""对话状态持久层。

封装对 dialogue_states 表的操作：
- load_state：根据用户 ID 查询对话状态，无记录时返回全新的 DialogueState；
- save_state：保存或更新对话状态（使用 MySQL 的 on_duplicate_key_update 实现 upsert）。
通过 pydantic 的 TypeAdapter 完成 DialogueState 与 JSON 字符串之间的序列化/反序列化。
"""
from pydantic import TypeAdapter
from sqlalchemy.dialects.mysql import insert, Insert
from sqlalchemy.ext.asyncio import AsyncSession

from consultant.domain.state import DialogueState
from consultant.models.dialogue_state_record import DialogueStateRecord

# DialogueState 的序列化适配器
DIALOGUE_STATE_ADAPTER = TypeAdapter(DialogueState)


class DialogueStateRecordRepository:
    """持久层：操作 dialogue_states 表"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def load_state(self, sender_id: str) -> DialogueState:
        """根据用户 ID（主键）查询对话状态"""
        record: DialogueStateRecord | None = await self.session.get(DialogueStateRecord, sender_id)
        if record is None:
            # 该用户第一次对话，返回全新的 DialogueState
            return DialogueState(sender_id=sender_id)
        # 将 state_json 字符串反序列化为 DialogueState
        return DIALOGUE_STATE_ADAPTER.validate_json(record.state_json)

    async def save_state(self, state: DialogueState):
        """保存或更新对话状态"""
        # 1. 将对话状态序列化为 JSON 字符串
        state_json = DIALOGUE_STATE_ADAPTER.dump_json(state).decode("utf-8")
        # 2. 构造 insert 语句
        insert_stmt: Insert = insert(DialogueStateRecord).values(
            sender_id=state.sender_id, state_json=state_json
        )
        # 3. 主键冲突时更新 state_json（upsert）
        update_stmt = insert_stmt.on_duplicate_key_update(
            state_json=insert_stmt.inserted.state_json
        )
        # 4. 执行并提交事务
        await self.session.execute(update_stmt)
        await self.session.commit()
