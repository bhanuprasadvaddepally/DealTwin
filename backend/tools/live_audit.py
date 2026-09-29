"""Run the live DealTwin audit against an isolated backend instance.

The script intentionally talks to the application HTTP API instead of mocking
Hindsight. It prints response evidence and checks the important contracts from
the product audit brief without printing environment variables or credentials.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def request(base_url: str, method: str, path: str, payload: dict | None = None, query: dict | None = None) -> tuple[int, dict]:
    url = f"{base_url.rstrip('/')}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=90) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"raw": raw}
        return exc.code, body
    except URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc.reason}") from exc


def expect(status: int, expected: int, label: str, body: dict) -> None:
    if status != expected:
        raise AssertionError(f"{label}: expected HTTP {expected}, received {status}: {body}")


def compact_memory(memory: dict) -> dict:
    return {
        "text": memory.get("text"),
        "source_chunk": memory.get("source_chunk"),
        "date": memory.get("date"),
        "relevance": memory.get("relevance"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8002")
    args = parser.parse_args()
    base_url = args.base_url
    suffix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    requested_deal_name = f"Acme Logistics expansion {suffix}"
    requested_empty_name = f"Empty audit deal {suffix}"
    deal_id = ""
    empty_deal_id = ""
    report: dict = {"base_url": base_url, "deal_id": deal_id, "checks": {}}

    status, health = request(base_url, "GET", "/health")
    expect(status, 200, "health", health)
    report["health"] = {
        "http_status": status,
        "status": health.get("status"),
        "backend": health.get("backend"),
        "database": health.get("database"),
        "hindsight_status": (health.get("hindsight") or {}).get("status"),
    }

    status, deal = request(
        base_url,
        "POST",
        "/api/deals",
        {
            "name": requested_deal_name,
            "company": "Acme Logistics",
            "contact_name": "Priya Shah",
            "location": "Hyderabad",
            "stage": "procurement review",
            "value": 240000,
            "decision_date": "2026-10-20",
        },
    )
    expect(status, 200, "create deal", deal)
    deal_id = deal["id"]
    report["deal_id"] = deal_id
    report["deal"] = {"id": deal.get("id"), "company": deal.get("company"), "decision_date": deal.get("decision_date")}

    interactions = [
        {
            "content": (
                "Acme Logistics is evaluating our logistics automation platform. Priya, the CTO, wants API integration "
                "and deployment in under six weeks. Rohan, the CFO, thinks the annual price is too high and prefers "
                "quarterly billing. They are evaluating CloudRoute. We promised to send the security documentation by "
                "25 September 2026."
            ),
            "interaction_date": "2026-09-14",
            "interaction_type": "meeting",
            "source": "audit interaction 1",
            "participants": ["Priya Shah", "Rohan Mehta"],
        },
        {
            "content": (
                "The technical workshop went well and Priya liked the API demonstration. The operations team still wants "
                "a migration plan and Meera, the Operations Director, asked for a phased rollout. The security "
                "documentation is still not sent. The customer wants a decision by 20 October 2026."
            ),
            "interaction_date": "2026-09-22",
            "interaction_type": "meeting",
            "source": "audit interaction 2",
            "participants": ["Priya Shah", "Meera Rao"],
        },
        {
            "content": (
                "Meera, the Operations Director, is concerned about migration disruption. Priya wants API support and a "
                "clear rollout plan. Rohan will approve a quarterly billing structure if the security review is complete."
            ),
            "interaction_date": "2026-09-23",
            "interaction_type": "call",
            "source": "audit interaction 3",
            "participants": ["Meera Rao", "Priya Shah", "Rohan Mehta"],
        },
    ]
    retained = []
    for index, interaction in enumerate(interactions, start=1):
        status, body = request(base_url, "POST", f"/api/deals/{deal_id}/interactions", interaction)
        expect(status, 200, f"retain interaction {index}", body)
        retained.append(body)
    status, duplicate = request(base_url, "POST", f"/api/deals/{deal_id}/interactions", interactions[0])
    expect(status, 200, "duplicate interaction", duplicate)
    report["retain"] = {
        "operations": [item.get("operation") for item in retained],
        "duplicate": duplicate,
    }

    status, memories = request(
        base_url,
        "GET",
        f"/api/deals/{deal_id}/memories",
        query={"query": "What billing preference did Rohan state?"},
    )
    expect(status, 200, "recall billing preference", memories)
    report["memory"] = {
        "count": memories.get("count"),
        "evidence": [compact_memory(item) for item in memories.get("memories", [])[:5]],
    }

    status, briefing = request(
        base_url,
        "POST",
        f"/api/deals/{deal_id}/briefing",
        {"question": "Prepare me for my next call with Acme Logistics."},
    )
    expect(status, 200, "briefing reflect", briefing)
    report["briefing"] = {
        "briefing": briefing.get("briefing"),
        "memory_count": len(briefing.get("supporting_memories", [])),
        "limitations": briefing.get("limitations"),
    }

    status, promise = request(base_url, "GET", f"/api/deals/{deal_id}/promise-debt")
    expect(status, 200, "promise debt", promise)
    report["promise_debt"] = {
        "score": promise.get("score"),
        "level": promise.get("level"),
        "explanation": promise.get("explanation"),
        "commitments": promise.get("affected_commitments"),
        "supporting_memory_count": len(promise.get("supporting_memories", [])),
    }

    status, simulation = request(
        base_url,
        "POST",
        f"/api/deals/{deal_id}/simulate",
        {
            "proposed_action": "Offer a 15% discount if Acme Logistics signs this month.",
            "requested_focus": "Rohan prefers quarterly billing and the security review is still open.",
        },
    )
    expect(status, 200, "simulation", simulation)
    report["simulation"] = {
        "confidence": simulation.get("confidence"),
        "possible_benefits": simulation.get("possible_benefits"),
        "risks": simulation.get("risks"),
        "stakeholder_reactions": simulation.get("stakeholder_reactions"),
        "recommended_alternative": simulation.get("recommended_alternative"),
        "recommended_sequence": simulation.get("recommended_sequence"),
        "supporting_memory_count": len(simulation.get("supporting_memories", [])),
        "limitations": simulation.get("limitations"),
    }

    status, stakeholders = request(base_url, "GET", f"/api/deals/{deal_id}/stakeholders")
    expect(status, 200, "stakeholders", stakeholders)
    report["stakeholders"] = stakeholders

    status, conversation = request(
        base_url,
        "POST",
        f"/api/deals/{deal_id}/conversation",
        {"content": "How should I talk about the migration risk on the next call?", "interaction_date": "2026-09-24"},
    )
    expect(status, 200, "conversation", conversation)
    report["conversation"] = {
        "outbound": conversation.get("outbound"),
        "retain_operation": conversation.get("retain_operation"),
        "reflect_memory_count": conversation.get("reflect_memory_count"),
        "supporting_memory_count": len(conversation.get("supporting_memories", [])),
    }

    status, outcome = request(
        base_url,
        "POST",
        f"/api/deals/{deal_id}/outcomes",
        {
            "action": "Proposed a phased migration workshop",
            "outcome": "positive response",
            "notes": "Accepted for procurement review; migration risk decreased.",
            "occurred_at": "2026-09-25T10:30:00Z",
        },
    )
    expect(status, 200, "outcome retain", outcome)
    status, outcome_memory = request(
        base_url,
        "GET",
        f"/api/deals/{deal_id}/memories",
        query={"query": "What happened after the phased migration workshop?"},
    )
    expect(status, 200, "outcome recall", outcome_memory)
    report["outcome"] = {
        "retain_operation": outcome.get("operation"),
        "outcome_id": outcome.get("outcome_id"),
        "recall_count": outcome_memory.get("count"),
        "recall_evidence": [compact_memory(item) for item in outcome_memory.get("memories", [])[:5]],
    }

    replay_question = "What should I address in the next Acme Logistics conversation?"
    status, before = request(base_url, "POST", "/api/demo/before-memory", {"question": replay_question})
    expect(status, 200, "before memory", before)
    status, after = request(
        base_url,
        "POST",
        "/api/demo/after-memory",
        {"deal_id": deal_id, "question": replay_question},
    )
    expect(status, 200, "after memory", after)
    report["replay"] = {
        "before": before,
        "after": {
            "label": after.get("label"),
            "answer": after.get("answer"),
            "memory_count": after.get("memory_count"),
            "reflect_memory_count": after.get("reflect_memory_count"),
            "supporting_memory_count": len(after.get("supporting_memories", [])),
        },
    }

    status, empty_deal = request(
        base_url,
        "POST",
        "/api/deals",
        {"name": requested_empty_name, "company": "No Activity Co", "stage": "discovery"},
    )
    expect(status, 200, "create empty deal", empty_deal)
    empty_deal_id = empty_deal["id"]
    empty_checks: dict = {}
    for label, method, path, payload in [
        ("empty_memories", "GET", f"/api/deals/{empty_deal_id}/memories", None),
        ("empty_promise_debt", "GET", f"/api/deals/{empty_deal_id}/promise-debt", None),
        ("empty_stakeholders", "GET", f"/api/deals/{empty_deal_id}/stakeholders", None),
        (
            "empty_simulation",
            "POST",
            f"/api/deals/{empty_deal_id}/simulate",
            {"proposed_action": "Offer a discount"},
        ),
    ]:
        status, body = request(base_url, method, path, payload)
        expect(status, 200, label, body)
        empty_checks[label] = body
    status, invalid = request(
        base_url,
        "POST",
        "/api/deals",
        {"name": "", "company": "Invalid", "stage": "discovery"},
    )
    expect(status, 422, "malformed create deal", invalid)
    report["empty_and_validation"] = {"checks": empty_checks, "malformed_create": invalid}

    report["checks"] = {
        "live_health": report["health"]["hindsight_status"] == "ok",
        "retain_completed": all(item.get("status") == "completed" for item in report["retain"]["operations"]),
        "duplicate_detected": report["retain"]["duplicate"].get("duplicate") is True,
        "recall_has_evidence": bool(report["memory"]["count"]),
        "briefing_has_evidence": report["briefing"]["memory_count"] > 0,
        "promise_has_overdue_item": any(item.get("status") == "overdue" for item in report["promise_debt"]["commitments"]),
        "simulation_is_cautious": report["simulation"]["confidence"] in {"low", "medium"} and bool(report["simulation"]["risks"]),
        "stakeholders_have_requested_people": all(
            any(person.get("name", "").lower().startswith(name.lower()) for person in report["stakeholders"].get("stakeholders", []))
            for name in ("Priya", "Rohan", "Meera")
        ),
        "outcome_recalled": report["outcome"]["recall_count"] > 0,
        "replay_uses_memory": report["replay"]["after"]["memory_count"] > 0 and report["replay"]["after"]["reflect_memory_count"] > 0,
        "empty_simulation_is_cautious": report["empty_and_validation"]["checks"]["empty_simulation"].get("confidence") == "low",
        "validation_is_safe": report["empty_and_validation"]["malformed_create"].get("error", {}).get("code") == "VALIDATION_ERROR",
    }

    print(json.dumps(report, indent=2, default=str))
    failed = [name for name, passed in report["checks"].items() if not passed]
    if failed:
        print(f"\nFAILED CHECKS: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("\nALL LIVE AUDIT CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
