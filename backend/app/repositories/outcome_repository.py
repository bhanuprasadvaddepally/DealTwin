from datetime import datetime, timezone
from uuid import uuid4

from ..schemas.outcome import OutcomeCreate
from .db import Database


class OutcomeRepository:
    def __init__(self, db: Database):
        self.db = db

    def create(self, deal_id: str, payload: OutcomeCreate) -> str:
        outcome_id = str(uuid4())
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO outcomes VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    outcome_id,
                    deal_id,
                    payload.action,
                    payload.outcome,
                    payload.notes,
                    payload.occurred_at.isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return outcome_id

