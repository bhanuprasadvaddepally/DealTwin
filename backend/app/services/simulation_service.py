from ..schemas.simulation import SimulationRequest, SimulationResponse
from .hindsight_service import HindsightService


class SimulationService:
    def __init__(self, hindsight: HindsightService):
        self.hindsight = hindsight

    async def simulate(self, deal_id: str, payload: SimulationRequest, has_activity: bool = True) -> SimulationResponse:
        query = (
            f"Evaluate proposed action: {payload.proposed_action}. "
            "Find current deal evidence, stakeholder reactions, similar past actions, and recorded outcomes."
        )
        if has_activity:
            recalled = await self.hindsight.recall_deal_memories(
                deal_id=deal_id,
                query=query,
                feature="time machine evidence",
                categories=["current deal", "stakeholders", "objections", "action outcomes", "similar situations"],
            )
            reflection, reflect_memories = await self.hindsight.reflect_on_deal(
                deal_id=deal_id,
                query=(
                    f"A salesperson is considering: {payload.proposed_action}. "
                    "Assess possible benefits, risks, stakeholder reactions, a safer alternative, and an ordered sequence. "
                    "Use only remembered evidence and say when evidence is insufficient."
                ),
                feature="time machine reflection",
            )
        else:
            recalled = []
            reflect_memories = []
            reflection = "No deal-specific Hindsight memory is available yet. Capture a conversation or interaction before relying on this assessment."
        evidence = reflect_memories or recalled
        corpus = " ".join((item.source_chunk or item.text) for item in evidence).lower()
        benefits: list[str] = []
        risks: list[str] = []
        reactions: list[str] = []
        if evidence:
            if any(word in payload.proposed_action.lower() for word in ("discount", "price", "pricing")):
                benefits.append("May reduce the annual-price friction recalled from the deal.") if "price" in corpus else benefits.append("May create a path to reopen commercial discussion.")
                risks.append("Could weaken value-based positioning while the recalled evidence still includes security and migration concerns.") if any(word in corpus for word in ("security", "migration")) else risks.append("Could trade margin for a response without proving that price is the only blocker.")
            if "quarterly billing" in corpus:
                benefits.append("Quarterly billing is a remembered preference and may address the commercial concern more directly.")
            for name in ("Priya", "Rohan", "Operations team"):
                if name.lower() in corpus:
                    reactions.append(f"{name}: reaction should be checked against the remembered priorities before acting.")
            if not benefits:
                benefits.append("The action can be tested against the remembered deal context before customer contact.")
            if not risks:
                risks.append("The recalled evidence does not establish that this action resolves the main customer concern.")
        else:
            benefits = ["No deal-specific benefit can be established from Hindsight evidence yet."]
            risks = ["Insufficient remembered evidence to assess this action safely."]
        alternative = "Use the remembered quarterly-billing preference as the first commercial test, then revisit discounting only if value and security concerns are addressed." if "quarterly billing" in corpus else "Ask one targeted discovery question to validate the active concern before changing commercial terms."
        sequence = ["Confirm the active customer concern.", "Check the relevant stakeholder's priority.", "Take the smallest reversible action.", "Record the customer response in Hindsight."]
        unresolved_risk = any(word in corpus for word in ("security", "migration", "not sent", "overdue", "concern", "at risk"))
        confidence = "low" if not evidence else "medium" if unresolved_risk or len(evidence) < 5 else "high"
        limitations = ["This is a grounded possibility assessment, not a guaranteed prediction."]
        if not evidence:
            limitations.insert(0, "No relevant Hindsight memories were found for this deal; historical pattern evidence is insufficient.")
        return SimulationResponse(
            deal_id=deal_id,
            proposed_action=payload.proposed_action,
            possible_benefits=benefits,
            risks=risks,
            stakeholder_reactions=reactions or ["No stakeholder reaction was recalled for this action."],
            recommended_alternative=alternative,
            recommended_sequence=sequence,
            confidence=confidence,
            supporting_memories=evidence,
            limitations=limitations,
            reflection=reflection,
        )

