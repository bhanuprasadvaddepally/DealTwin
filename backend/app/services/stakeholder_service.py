import re

from ..schemas.memory import MemoryEvidence
from ..schemas.stakeholder import Stakeholder, StakeholderResponse
from .hindsight_service import HindsightService


class StakeholderService:
    def __init__(self, hindsight: HindsightService):
        self.hindsight = hindsight

    async def list(self, deal_id: str) -> StakeholderResponse:
        memories = await self.hindsight.recall_deal_memories(
            deal_id=deal_id,
            query="Identify every person or team involved, their role, influence, sentiment, priorities, objections, and relationship status.",
            feature="stakeholders",
            categories=["people", "roles", "sentiment", "priorities", "objections"],
        )
        buckets: dict[str, list[MemoryEvidence]] = {}
        person_names: set[str] = set()
        ignored_pairs = {
            "Acme Logistics",
            "Cloud Route",
            "Deal Twin",
            "Original Interaction",
            "Positive Response",
            "Security Documentation",
            "The Team",
            "The Customer",
            "When Involving",
        }
        ignored_words = {
            "Acme", "CloudRoute", "Deal", "Twin", "Original", "Interaction", "Positive", "Response",
            "Security", "Documentation", "The", "Team", "Customer", "When", "Involving", "Phased",
            "Migration", "Operations", "Director", "User", "Preparation", "Future", "Business", "Context",
        }
        unique_memories: dict[str, MemoryEvidence] = {}
        for memory in memories:
            text = memory.source_chunk or memory.text
            unique_memories[memory.memory_id or text] = memory
            for first, last in re.findall(r"\b([A-Z][a-z]{2,})\s+([A-Z][a-z]{2,})\b", text):
                full_name = f"{first} {last}"
                if full_name not in ignored_pairs and first not in ignored_words and last not in ignored_words:
                    person_names.add(full_name)
            if "operations team" in text.lower() or "operations" in text.lower():
                buckets.setdefault("Operations team", []).append(memory)
        memories = list(unique_memories.values())
        for name in sorted(person_names):
            first_name = name.split()[0]
            buckets[name] = [
                memory
                for memory in memories
                if re.search(rf"\b{re.escape(name)}\b", memory.source_chunk or memory.text, re.I)
                or re.search(rf"\b{re.escape(first_name)}\b", memory.source_chunk or memory.text, re.I)
            ]
        stakeholders: list[Stakeholder] = []
        for name, evidence in buckets.items():
            evidence = list({item.memory_id or item.text: item for item in evidence}.values())
            joined = " ".join((item.source_chunk or item.text) for item in evidence)
            lower = joined.lower()
            role = "unknown"
            role_match = re.search(rf"{re.escape(name)}\s*\(([^)]+)\)", joined, re.I)
            if not role_match:
                role_match = re.search(
                    rf"{re.escape(name)},?\s+(?:the\s+)?((?:CTO|CFO|Operations Director|Director|VP|Vice President|CEO|Buyer|Procurement)[A-Za-z ]*)",
                    joined,
                    re.I,
                )
            if role_match and role_match.group(1).strip().lower() not in {"the"}:
                role = role_match.group(1).strip().lower()
            if name == "Operations team":
                role = "operations evaluator"
            influence = "high" if any(role_word in role for role_word in ("cto", "cfo", "buyer", "decision")) else "medium" if role != "unknown" else "possible"
            positive = any(word in lower for word in ("interested", "liked", "accepted", "good"))
            concern = any(word in lower for word in ("too high", "security", "not sent", "wants", "prefers"))
            sentiment = "positive" if positive and not concern else "mixed" if positive and concern else "concerned" if concern else "unknown"
            concerns = []
            for keyword, label in (("api", "API integration"), ("deployment", "deployment time"), ("price", "annual price"), ("billing", "quarterly billing"), ("migration", "migration plan"), ("security", "security documentation")):
                if keyword in lower:
                    concerns.append(label)
            status = "supporting" if positive and not concern else "at risk" if concern else "unknown"
            stakeholders.append(Stakeholder(
                name=name,
                role=role,
                influence=influence,
                sentiment=sentiment,
                priority=concerns[0] if concerns else "unknown",
                concerns=concerns,
                relationship_status=status,
                last_interaction_date=str(evidence[0].date) if evidence[0].date else None,
                evidence=evidence[:4],
            ))
        stakeholders.sort(key=lambda item: (item.influence != "high", item.name))
        next_contact = None
        rationale = None
        for item in stakeholders:
            if item.relationship_status == "at risk":
                next_contact = item.name
                rationale = f"Contact {item.name} next because recalled evidence shows {', '.join(item.concerns) or 'an unresolved concern'} and the relationship is marked at risk."
                break
        return StakeholderResponse(stakeholders=stakeholders, recommended_next_contact=next_contact, rationale=rationale)

