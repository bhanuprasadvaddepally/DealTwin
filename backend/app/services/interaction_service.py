from ..core.errors import NotFoundError
from ..repositories.deal_repository import DealRepository
from ..repositories.interaction_repository import InteractionRepository
from ..schemas.interaction import InteractionCreate, InteractionResponse
from .hindsight_service import HindsightService


class InteractionService:
    def __init__(self, deals: DealRepository, interactions: InteractionRepository, hindsight: HindsightService):
        self.deals = deals
        self.interactions = interactions
        self.hindsight = hindsight

    async def retain(self, deal_id: str, payload: InteractionCreate) -> InteractionResponse:
        if not self.deals.get(deal_id):
            raise NotFoundError("Deal")
        existing_id = self.interactions.find_existing(deal_id, payload)
        if existing_id:
            return InteractionResponse(
                interaction_id=existing_id,
                deal_id=deal_id,
                duplicate=True,
                operation={"status": "already_retained", "operation": "retain", "message": "Duplicate interaction was not retained again."},
            )
        result = await self.hindsight.retain_interaction(
            deal_id=deal_id,
            interaction_date=payload.interaction_date,
            interaction_type=payload.interaction_type,
            content=payload.content,
            source=payload.source,
            participants=payload.participants,
        )
        interaction_id = self.interactions.create(deal_id, payload)
        return InteractionResponse(
            interaction_id=interaction_id,
            deal_id=deal_id,
            duplicate=False,
            operation={"status": result["status"], "operation": "retain", "trace_id": result["trace_id"], "message": "Hindsight retain completed."},
        )

