from datetime import date as date_type

from .common import APIModel


class MemoryEvidence(APIModel):
    memory_id: str | None = None
    text: str
    source_chunk: str | None = None
    date: date_type | None = None
    relevance: float | None = None
    feature_that_used_it: str


class MemoryListResponse(APIModel):
    query: str
    count: int
    memories: list[MemoryEvidence]

