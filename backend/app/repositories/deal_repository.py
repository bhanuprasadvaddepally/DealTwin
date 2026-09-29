from datetime import date, datetime, timezone
from uuid import uuid4

from ..schemas.deal import Deal, DealCreate
from .db import Database


class DealRepository:
    def __init__(self, db: Database):
        self.db = db

    def create(self, payload: DealCreate, deal_id: str | None = None) -> Deal:
        now = datetime.now(timezone.utc)
        result = Deal(
            id=deal_id or str(uuid4()),
            name=payload.name,
            company=payload.company,
            contact_name=payload.contact_name,
            location=payload.location,
            stage=payload.stage,
            value=payload.value,
            decision_date=payload.decision_date,
            created_at=now,
            updated_at=now,
        )
        with self.db.connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO deals (id, name, company, contact_name, location, stage, value, decision_date, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    result.id,
                    result.name,
                    result.company,
                    result.contact_name,
                    result.location,
                    result.stage,
                    result.value,
                    result.decision_date.isoformat() if result.decision_date else None,
                    result.created_at.isoformat(),
                    result.updated_at.isoformat(),
                ),
            )
        return result

    def get(self, deal_id: str) -> Deal | None:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
        if not row:
            return None
        return Deal(
            id=row["id"],
            name=row["name"],
            company=row["company"],
            contact_name=row["contact_name"],
            location=row["location"],
            stage=row["stage"],
            value=row["value"],
            decision_date=date.fromisoformat(row["decision_date"]) if row["decision_date"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def list(self) -> list[Deal]:
        with self.db.connection() as conn:
            rows = conn.execute("SELECT * FROM deals ORDER BY updated_at DESC").fetchall()
        return [self._from_row(row) for row in rows]

    def has_activity(self, deal_id: str) -> bool:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT EXISTS (SELECT 1 FROM interactions WHERE deal_id = ? UNION ALL SELECT 1 FROM outcomes WHERE deal_id = ?)",
                (deal_id, deal_id),
            ).fetchone()
        return bool(row[0])

    def delete(self, deal_id: str) -> bool:
        with self.db.connection() as conn:
            conn.execute("DELETE FROM interactions WHERE deal_id = ?", (deal_id,))
            conn.execute("DELETE FROM outcomes WHERE deal_id = ?", (deal_id,))
            result = conn.execute("DELETE FROM deals WHERE id = ?", (deal_id,))
        return result.rowcount > 0

    @staticmethod
    def _from_row(row) -> Deal:
        return Deal(
            id=row["id"],
            name=row["name"],
            company=row["company"],
            contact_name=row["contact_name"],
            location=row["location"],
            stage=row["stage"],
            value=row["value"],
            decision_date=date.fromisoformat(row["decision_date"]) if row["decision_date"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

