from pydantic import Field

from .common import APIModel
from .memory import MemoryEvidence


class BriefingRequest(APIModel):
    question: str = Field(default="Prepare me for my next call.", min_length=1, max_length=1000)


class BriefingResponse(APIModel):
    label: str
    briefing: str
    supporting_memories: list[MemoryEvidence]
    limitations: list[str]


class ReplayRequest(APIModel):
    question: str = Field(min_length=1, max_length=1000)


class BeforeMemoryResponse(APIModel):
    label: str
    answer: str
    supporting_memories: list[MemoryEvidence]


class AfterMemoryRequest(APIModel):
    deal_id: str
    question: str = Field(min_length=1, max_length=1000)


class AfterMemoryResponse(APIModel):
    label: str
    answer: str
    supporting_memories: list[MemoryEvidence]
    memory_count: int
    reflect_memory_count: int

