from datetime import date
from typing import Literal

from pydantic import Field

from .common import APIModel, OperationStatus


InteractionType = Literal["meeting", "call", "email", "note", "transcript"]


class InteractionCreate(APIModel):
    content: str = Field(min_length=1, max_length=20000)
    interaction_date: date
    interaction_type: InteractionType
    source: str | None = Field(default=None, max_length=160)
    participants: list[str] = Field(default_factory=list, max_length=30)


class InteractionResponse(APIModel):
    interaction_id: str
    deal_id: str
    duplicate: bool
    operation: OperationStatus

