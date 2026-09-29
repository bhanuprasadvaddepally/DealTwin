from datetime import datetime
from typing import Literal

from pydantic import Field

from .common import APIModel, OperationStatus


OutcomeType = Literal[
    "positive response",
    "no response",
    "objection increased",
    "meeting scheduled",
    "deal advanced",
    "deal stalled",
    "deal won",
    "deal lost",
]


class OutcomeCreate(APIModel):
    action: str = Field(min_length=1, max_length=2000)
    outcome: OutcomeType
    notes: str = Field(default="", max_length=10000)
    occurred_at: datetime


class OutcomeResponse(APIModel):
    outcome_id: str
    operation: OperationStatus

