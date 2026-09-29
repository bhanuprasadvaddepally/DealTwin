from datetime import date, datetime

from pydantic import Field

from .common import APIModel


class DealCreate(APIModel):
    name: str = Field(min_length=1, max_length=160)
    company: str = Field(min_length=1, max_length=160)
    contact_name: str | None = Field(default=None, max_length=160)
    location: str | None = Field(default=None, max_length=160)
    stage: str = Field(default="discovery", min_length=1, max_length=80)
    value: float | None = Field(default=None, ge=0)
    decision_date: date | None = None


class Deal(APIModel):
    id: str
    name: str
    company: str
    contact_name: str | None = None
    location: str | None = None
    stage: str
    value: float | None
    decision_date: date | None
    created_at: datetime
    updated_at: datetime

