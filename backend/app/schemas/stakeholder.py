from .common import APIModel
from .memory import MemoryEvidence


class Stakeholder(APIModel):
    name: str
    role: str
    influence: str
    sentiment: str
    priority: str
    concerns: list[str]
    relationship_status: str
    last_interaction_date: str | None = None
    evidence: list[MemoryEvidence]


class StakeholderResponse(APIModel):
    stakeholders: list[Stakeholder]
    recommended_next_contact: str | None = None
    rationale: str | None = None

