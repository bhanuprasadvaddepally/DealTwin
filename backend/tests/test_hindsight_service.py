import pytest

from app.core.errors import HindsightUnavailable


@pytest.mark.asyncio
async def test_retain_payload_contains_deal_context(service, fake_client):
    result = await service.retain_interaction(
        deal_id="deal-123",
        interaction_date=__import__("datetime").date(2026, 9, 29),
        interaction_type="meeting",
        content="The buyer prefers quarterly billing.",
        source="call notes",
        participants=["Rohan"],
    )
    assert result["status"] == "completed"
    assert fake_client.retained[0]["bank_id"] == "test-bank"
    assert "deal-123" in fake_client.retained[0]["content"]
    assert "quarterly billing" in fake_client.retained[0]["content"]


@pytest.mark.asyncio
async def test_recall_query_contains_deal_and_question(service, fake_client):
    await service.recall_deal_memories(deal_id="deal-123", query="Who is the buyer?", feature="test")
    query = fake_client.recall_queries[0]
    assert "deal-123" in query
    assert "Who is the buyer?" in query


@pytest.mark.asyncio
async def test_reflect_returns_evidence(service, fake_client):
    fake_client.memories = ["Priya owns API integration."]
    answer, evidence = await service.reflect_on_deal(deal_id="deal-123", query="Prepare me", feature="test")
    assert answer.startswith("Grounded")
    assert evidence[0].text == "Priya owns API integration."
    assert fake_client.reflect_queries


@pytest.mark.asyncio
async def test_hindsight_failure_is_converted(settings):
    from tests.conftest import FakeHindsightClient

    failing = __import__("app.services.hindsight_service", fromlist=["HindsightService"]).HindsightService(settings, client=FakeHindsightClient(fail=True))
    with pytest.raises(HindsightUnavailable):
        await failing.retain_action_outcome(deal_id="deal-123", action="call", outcome="no response", notes="", occurred_at="2026-09-29T12:00:00Z")

