from datetime import date
from typing import Literal

from .common import APIModel
from .memory import MemoryEvidence


class Commitment(APIModel):
    text: str
    deal_id: str
    owner: str | None = None
    recipient: str | None = None
    due_date: date | None = None
    status: Literal["pending", "completed", "overdue", "cancelled", "unknown"]
    related_stakeholder: str | None = None
    related_objection: str | None = None
    importance: str
    evidence: list[MemoryEvidence]


class PromiseDebtResponse(APIModel):
    score: int
    level: Literal["low", "medium", "high"]
    explanation: str
    affected_commitments: list[Commitment]
    supporting_memories: list[MemoryEvidence]
    recommended_remediation: str

