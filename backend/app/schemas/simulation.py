from typing import Literal

from pydantic import Field

from .common import APIModel
from .memory import MemoryEvidence


class SimulationRequest(APIModel):
    proposed_action: str = Field(min_length=1, max_length=2000)
    requested_focus: str | None = Field(default=None, max_length=500)


class SimulationResponse(APIModel):
    deal_id: str
    proposed_action: str
    possible_benefits: list[str]
    risks: list[str]
    stakeholder_reactions: list[str]
    recommended_alternative: str
    recommended_sequence: list[str]
    confidence: Literal["low", "medium", "high"]
    supporting_memories: list[MemoryEvidence]
    limitations: list[str]
    reflection: str

