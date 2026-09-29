import re
from datetime import date, datetime, timedelta

from ..schemas.memory import MemoryEvidence
from ..schemas.promise import Commitment, PromiseDebtResponse
from .hindsight_service import HindsightService


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]


def _date_from_text(text: str, today: date, base_date: date | None = None) -> date | None:
    inline_date = re.search(r"\bWhen:\s*(\d{4}-\d{2}-\d{2})\b", text, re.I)
    if inline_date:
        return date.fromisoformat(inline_date.group(1))
    weekday_match = re.search(r"(?:\bdecision\s+by\b|\bby\b|\bdue\b)\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)", text, re.I)
    if weekday_match:
        anchor = base_date or today
        target = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}[weekday_match.group(1).lower()]
        return anchor + timedelta(days=(target - anchor.weekday()) % 7 or 7)
    month_first = re.search(
        r"(?:\bdecision\s+by\b|\bon\b|\bby\b|\bdue\b|\bdeadline\b)\s+([A-Za-z]+)\s+(\d{1,2})(?:,\s*(\d{4}))?",
        text,
        re.I,
    )
    if month_first:
        year = int(month_first.group(3) or today.year)
        for pattern in ("%B %d %Y", "%b %d %Y"):
            try:
                return datetime.strptime(f"{month_first.group(1)} {month_first.group(2)} {year}", pattern).date()
            except ValueError:
                continue
        return None
    match = re.search(r"(?:\bdecision\s+by\b|\bby\b|\bdue\b|\bdeadline\b)\s+(\d{1,2})\s+([A-Za-z]+)(?:,?\s*(\d{4}))?", text, re.I)
    if not match:
        return None
    try:
        parsed = datetime.strptime(f"{match.group(1)} {match.group(2)} {match.group(3) or today.year}", "%d %B %Y").date()
    except ValueError:
        try:
            parsed = datetime.strptime(f"{match.group(1)} {match.group(2)} {match.group(3) or today.year}", "%d %b %Y").date()
        except ValueError:
            return None
    return parsed


def extract_commitments(memories: list[MemoryEvidence], deal_id: str, today: date | None = None) -> list[Commitment]:
    today = today or date.today()
    found: list[Commitment] = []
    seen: set[str] = set()
    for memory in memories:
        source = memory.source_chunk or memory.text
        for sentence in _sentences(source):
            lower = sentence.lower()
            if not any(word in lower for word in ("promis", "commit", "send", "sent", "schedule", "scheduled", "provide", "deliver")):
                continue
            if sentence.lower() in seen:
                continue
            seen.add(sentence.lower())
            base_date_match = re.search(r"date=(\d{4}-\d{2}-\d{2})", source)
            base_date = date.fromisoformat(base_date_match.group(1)) if base_date_match else memory.date
            due = _date_from_text(sentence, today, base_date) or _date_from_text(source, today, base_date)
            unresolved = any(word in lower for word in ("not sent", "has not", "haven't", "missed", "overdue", "still open", "outstanding"))
            completed = any(word in lower for word in ("has been sent", "was sent", "delivered", "completed", "done")) and not unresolved
            if completed:
                status = "completed"
            elif due and due < today and (unresolved or "promis" in lower or "commit" in lower):
                status = "overdue"
            else:
                status = "pending"
            if any(word in lower for word in ("cancelled", "canceled")):
                status = "cancelled"
            stakeholder = None
            for candidate in ("Priya", "Rohan"):
                if candidate.lower() in lower:
                    stakeholder = candidate
                    break
            objection = "security concern" if "security" in lower else None
            importance = "high" if objection or status == "overdue" else "medium"
            found.append(
                Commitment(
                    text=sentence,
                    deal_id=deal_id,
                    owner=None,
                    recipient=stakeholder,
                    due_date=due,
                    status=status,
                    related_stakeholder=stakeholder,
                    related_objection=objection,
                    importance=importance,
                    evidence=[memory],
                )
            )
    return found


class PromiseDebtService:
    def __init__(self, hindsight: HindsightService):
        self.hindsight = hindsight

    async def calculate(self, deal_id: str) -> PromiseDebtResponse:
        memories = await self.hindsight.recall_deal_memories(
            deal_id=deal_id,
            query="Find every commitment, promised deliverable, due date, missed promise, active objection, and decision deadline.",
            feature="promise debt",
            categories=["commitments", "deadlines", "objections", "decision dates"],
        )
        commitments = extract_commitments(memories, deal_id)
        score = 0
        overdue = [item for item in commitments if item.status == "overdue"]
        active_objection = [item for item in commitments if item.related_objection]
        score += 20 if overdue else 0
        score += 25 if active_objection else 0
        corpus = " ".join((item.source_chunk or item.text) for item in memories)
        decision_matches = re.findall(r"decision\s+by\s+(?:\d{1,2}\s+[A-Za-z]+|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)", corpus, re.I)
        decision_dates = {
            parsed
            for phrase in decision_matches
            if (parsed := _date_from_text(phrase, date.today())) is not None
        }
        decision_date = next(iter(decision_dates)) if len(decision_dates) == 1 else None
        approaching = bool(decision_date and 0 <= (decision_date - date.today()).days <= 30)
        score += 20 if approaching else 0
        score += 15 if len(overdue) > 1 else 0
        score = min(100, score)
        level = "high" if score >= 60 else "medium" if score >= 30 else "low"
        reasons: list[str] = []
        if overdue:
            reasons.append(f"{len(overdue)} commitment{'s are' if len(overdue) != 1 else ' is'} overdue")
        if active_objection:
            reasons.append("at least one commitment is linked to an active concern")
        if approaching:
            reasons.append("a decision deadline is approaching")
        if len(decision_dates) > 1:
            explanation = "Conflicting evidence found: two decision dates were recalled. Please confirm the current date."
        else:
            explanation = f"Follow-up risk is {level.title()} ({score}/100)" + (" because " + ", ".join(reasons) + "." if reasons else "; no important follow-up risk was found in the saved client notes.")
        remediation = "Confirm the owner and send the overdue deliverable before the next customer touchpoint." if overdue else "Keep owners and due dates explicit in the next interaction."
        return PromiseDebtResponse(
            score=score,
            level=level,
            explanation=explanation,
            affected_commitments=commitments,
            supporting_memories=memories,
            recommended_remediation=remediation,
        )

