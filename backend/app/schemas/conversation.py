from datetime import date

from pydantic import Field

from .common import APIModel, OperationStatus
from .memory import MemoryEvidence


class ConversationMessageCreate(APIModel):
    content: str = Field(min_length=1, max_length=10000)
    interaction_date: date


class ConversationMessageResponse(APIModel):
    deal_id: str
    inbound: str
    outbound: str
    retain_operation: OperationStatus
    reflect_memory_count: int
    supporting_memories: list[MemoryEvidence]

