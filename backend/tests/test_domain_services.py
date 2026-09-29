from datetime import date

import pytest

from app.schemas.memory import MemoryEvidence
from app.services.promise_debt_service import _date_from_text, extract_commitments
from app.services.stakeholder_service import StakeholderService


def evidence(text: str) -> MemoryEvidence:
    return MemoryEvidence(text=text, source_chunk=text, feature_that_used_it="test")


def test_promise_debt_extraction_marks_overdue_commitment():
    memories = [evidence("We promised to send the security documentation by 18 September. The security document has not been sent yet.")]
    commitments = extract_commitments(memories, "acme", today=date(2026, 9, 29))
    assert commitments
    assert any(item.status == "overdue" for item in commitments)
    assert any(item.related_objection == "security concern" for item in commitments)


def test_empty_memories_do_not_invent_commitments():
    assert extract_commitments([], "new-deal", today=date(2026, 9, 29)) == []


def test_date_parser_does_not_silently_merge_conflicting_dates():
    first = _date_from_text("decision by 20 October", date(2026, 9, 29))
    second = _date_from_text("decision by 25 October", date(2026, 9, 29))
    assert first != second


def test_promise_debt_reads_hindsight_inline_dates_and_completed_state():
    overdue = extract_commitments(
        [evidence("We committed to send security documentation. | When: 2026-09-25")],
        "acme",
        today=date(2026, 9, 29),
    )
    completed = extract_commitments(
        [evidence("The security documentation has been sent and is complete. | When: 2026-09-25")],
        "acme",
        today=date(2026, 9, 29),
    )
    assert overdue[0].due_date == date(2026, 9, 25)
    assert overdue[0].status == "overdue"
    assert completed[0].status == "completed"


def test_promise_debt_keeps_future_and_no_date_commitments_distinct():
    future = extract_commitments(
        [evidence("We promised to send the rollout plan by October 30, 2026.")],
        "acme",
        today=date(2026, 9, 29),
    )
    no_date = extract_commitments(
        [evidence("We promised to send the rollout plan soon.")],
        "acme",
        today=date(2026, 9, 29),
    )
    assert future[0].due_date == date(2026, 10, 30)
    assert future[0].status == "pending"
    assert no_date[0].due_date is None
    assert no_date[0].status == "pending"


def test_promise_debt_preserves_conflicting_dates_for_review():
    memories = [
        evidence("We promised to send the security documentation by 25 September, 2026."),
        evidence("We later committed to send the security documentation by 30 September, 2026."),
    ]
    commitments = extract_commitments(memories, "acme", today=date(2026, 9, 29))
    assert {item.due_date for item in commitments} == {date(2026, 9, 25), date(2026, 9, 30)}


class MemoryProvider:
    async def recall_deal_memories(self, **kwargs):
        return [
            evidence("Priya Shah (CTO) needs API support. | When: 2026-09-23 | Involving: Priya Shah"),
            evidence("Rohan Mehta (CFO) prefers quarterly billing. | When: 2026-09-23 | Involving: Rohan Mehta"),
            evidence("Meera Rao (Operations Director) is concerned about migration disruption."),
        ]


@pytest.mark.asyncio
async def test_stakeholder_extraction_keeps_people_and_team_names_clean():
    response = await StakeholderService(MemoryProvider()).list("acme")
    names = {item.name for item in response.stakeholders}
    assert {"Priya Shah", "Rohan Mehta", "Meera Rao"}.issubset(names)
    assert "Acme" not in names
    assert "When" not in names

