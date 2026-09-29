from ..schemas.conversation import ConversationMessageCreate, ConversationMessageResponse
from ..schemas.interaction import InteractionCreate
from .briefing_service import BriefingService
from .hindsight_service import HindsightService
from .interaction_service import InteractionService


class ConversationService:
    def __init__(self, interactions: InteractionService, hindsight: HindsightService):
        self.interactions = interactions
        self.hindsight = hindsight

    async def respond(self, deal_id: str, payload: ConversationMessageCreate) -> ConversationMessageResponse:
        retained = await self.interactions.retain(
            deal_id,
            InteractionCreate(
                content=payload.content,
                interaction_date=payload.interaction_date,
                interaction_type="note",
                source="prospect conversation",
                participants=[],
            ),
        )
        briefing = await BriefingService(self.hindsight).prepare(deal_id, payload.content)
        return ConversationMessageResponse(
            deal_id=deal_id,
            inbound=payload.content,
            outbound=briefing.briefing,
            retain_operation=retained.operation,
            reflect_memory_count=len(briefing.supporting_memories),
            supporting_memories=briefing.supporting_memories,
        )
