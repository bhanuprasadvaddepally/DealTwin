from ..schemas.intelligence import BriefingResponse
from .hindsight_service import HindsightService


class BriefingService:
    def __init__(self, hindsight: HindsightService):
        self.hindsight = hindsight

    async def prepare(self, deal_id: str, question: str) -> BriefingResponse:
        text, reflect_memories = await self.hindsight.reflect_on_deal(
            deal_id=deal_id,
            query=f"Prepare a concise next-call briefing for this question: {question}",
            feature="briefing",
        )
        recalled = await self.hindsight.recall_deal_memories(
            deal_id=deal_id,
            query=question,
            feature="briefing evidence",
        )
        evidence = reflect_memories or recalled
        return BriefingResponse(
            label="With Hindsight memory",
            briefing=text,
            supporting_memories=evidence,
            limitations=[] if evidence else ["No relevant memory was found; this briefing is not personalized."],
        )

