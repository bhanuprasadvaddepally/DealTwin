from ..repositories.outcome_repository import OutcomeRepository
from ..schemas.outcome import OutcomeCreate, OutcomeResponse
from .hindsight_service import HindsightService


class OutcomeService:
    def __init__(self, outcomes: OutcomeRepository, hindsight: HindsightService):
        self.outcomes = outcomes
        self.hindsight = hindsight

    async def record(self, deal_id: str, payload: OutcomeCreate) -> OutcomeResponse:
        result = await self.hindsight.retain_action_outcome(
            deal_id=deal_id,
            action=payload.action,
            outcome=payload.outcome,
            notes=payload.notes,
            occurred_at=payload.occurred_at.isoformat(),
        )
        outcome_id = self.outcomes.create(deal_id, payload)
        return OutcomeResponse(
            outcome_id=outcome_id,
            operation={"status": result["status"], "operation": "retain", "trace_id": result["trace_id"], "message": "Action outcome retained in Hindsight."},
        )

