"""对话业务层。

职责：
1. 加载对话状态；
2. 调用对话引擎处理消息（修改对话状态），得到客服回复；
3. 保存 / 更新对话状态；
4. 返回本轮回复结果。
"""
from consultant.domain.messages import UserMessage, ProcessResult
from consultant.domain.state import DialogueState
from consultant.engine.dialogue_engine import DialogueEngine
from consultant.repository.dialogue_state_record_repository import DialogueStateRecordRepository


class DialogueService:

    def __init__(self, dialogue_state_repository: DialogueStateRecordRepository,
                 dialogue_engine: DialogueEngine):
        self.dialogue_state_repository = dialogue_state_repository
        self.dialogue_engine = dialogue_engine

    async def process_message(self, user_message: UserMessage) -> ProcessResult:
        """处理本轮消息"""
        # 1. 根据用户 ID 加载对话状态
        state: DialogueState = await self.dialogue_state_repository.load_state(user_message.sender_id)
        # 2. 调用对话引擎处理，得到客服回复
        process_result: ProcessResult = await self.dialogue_engine.process_message(state, user_message)
        # 3. 保存 / 更新对话状态
        await self.dialogue_state_repository.save_state(state)
        # 4. 返回结果
        return process_result

    async def get_state(self, sender_id: str) -> DialogueState:
        """查询当前用户对话状态"""
        return await self.dialogue_state_repository.load_state(sender_id)
