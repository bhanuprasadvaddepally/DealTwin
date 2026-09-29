import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from ..schemas.interaction import InteractionCreate
from .db import Database


class InteractionRepository:
    def __init__(self, db: Database):
        self.db = db

    def _hash(self, deal_id: str, payload: InteractionCreate) -> str:
        raw = "|".join(
            [deal_id, payload.content.strip(), payload.interaction_date.isoformat(), payload.interaction_type]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def find_existing(self, deal_id: str, payload: InteractionCreate) -> str | None:
        content_hash = self._hash(deal_id, payload)
        with self.db.connection() as conn:
            existing = conn.execute(
                "SELECT id FROM interactions WHERE content_hash = ?", (content_hash,)
            ).fetchone()
        return existing["id"] if existing else None

    def create(self, deal_id: str, payload: InteractionCreate) -> str:
        content_hash = self._hash(deal_id, payload)
        interaction_id = str(uuid4())
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO interactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    interaction_id,
                    deal_id,
                    content_hash,
                    payload.interaction_date.isoformat(),
                    payload.interaction_type,
                    payload.source,
                    json.dumps(payload.participants),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return interaction_id

