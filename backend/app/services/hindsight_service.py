import importlib.metadata
import logging
import re
import time
from datetime import date
from typing import Any

import httpx

from ..config import Settings
from ..core.errors import HindsightUnavailable
from ..schemas.memory import MemoryEvidence

logger = logging.getLogger(__name__)


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


class HindsightService:
    """The only application boundary allowed to call Hindsight."""

    def __init__(self, settings: Settings, client: Any | None = None):
        self.settings = settings
        self._client_override = client
        self._client_instance: Any | None = None

    def _client(self) -> Any:
        if self._client_override is not None:
            return self._client_override
        if self._client_instance is not None:
            return self._client_instance
        try:
            from hindsight_client import Hindsight
        except ImportError as exc:
            raise HindsightUnavailable("Install the hindsight-client package.") from exc
        self._client_instance = Hindsight(
            base_url=self.settings.hindsight_base_url,
            api_key=self.settings.hindsight_api_key or None,
            timeout=self.settings.hindsight_timeout_seconds,
            max_attempts=2,
            user_agent="dealtwin/0.1",
        )
        return self._client_instance

    async def close(self) -> None:
        if self._client_instance is None:
            return
        close = getattr(self._client_instance, "aclose", None)
        if close is not None:
            await close()
        self._client_instance = None

    def _evidence(self, item: Any, feature: str, chunks: dict[str, Any] | None = None) -> MemoryEvidence:
        memory_id = _get(item, "id") or _get(item, "memory_id")
        source_chunk = None
        if chunks and memory_id in chunks:
            chunk = chunks[memory_id]
            source_chunk = _get(chunk, "text") or str(chunk)
        raw_date = _get(item, "date") or _get(item, "created_at")
        if not raw_date:
            dated_text = str(_get(item, "text") or _get(item, "content") or "")
            date_match = re.search(r"\bWhen:\s*(\d{4}-\d{2}-\d{2})\b", dated_text)
            raw_date = date_match.group(1) if date_match else None
        parsed_date = None
        if raw_date:
            try:
                parsed_date = date.fromisoformat(str(raw_date)[:10])
            except ValueError:
                parsed_date = None
        return MemoryEvidence(
            memory_id=str(memory_id) if memory_id else None,
            text=str(_get(item, "text") or _get(item, "content") or item),
            source_chunk=source_chunk,
            date=parsed_date,
            relevance=float(_get(item, "score")) if _get(item, "score") is not None else None,
            feature_that_used_it=feature,
        )

    async def retain_interaction(
        self,
        *,
        deal_id: str,
        interaction_date: date,
        interaction_type: str,
        content: str,
        source: str | None,
        participants: list[str],
    ) -> dict[str, Any]:
        enriched = (
            f"DealTwin interaction. deal_id={deal_id}; date={interaction_date.isoformat()}; "
            f"type={interaction_type}; source={source or 'unspecified'}; "
            f"participants={', '.join(participants) or 'unspecified'}.\nOriginal interaction:\n{content}"
        )
        return await self._retain(enriched, f"deal interaction {deal_id}")

    async def retain_action_outcome(
        self, *, deal_id: str, action: str, outcome: str, notes: str, occurred_at: str
    ) -> dict[str, Any]:
        enriched = (
            f"DealTwin action outcome. deal_id={deal_id}; occurred_at={occurred_at}; "
            f"action={action}; outcome={outcome}.\nOutcome notes:\n{notes or 'none'}"
        )
        return await self._retain(enriched, f"action outcome {deal_id}")

    async def _retain(self, content: str, context: str) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            response = await self._client().aretain(
                bank_id=self.settings.hindsight_bank_id,
                content=content,
                context=context,
            )
        except Exception as exc:  # SDK exceptions vary by version.
            logger.warning("hindsight operation=retain duration_ms=%.1f error=%s", (time.perf_counter() - started) * 1000, type(exc).__name__)
            raise HindsightUnavailable() from exc
        duration = (time.perf_counter() - started) * 1000
        trace_id = _get(response, "operation_id") or _get(response, "trace_id") or _get(response, "id")
        logger.info("hindsight operation=retain duration_ms=%.1f", duration)
        return {"status": "completed", "trace_id": str(trace_id) if trace_id else None, "response": response}

    async def recall_deal_memories(
        self, *, deal_id: str, query: str, feature: str, categories: list[str] | None = None
    ) -> list[MemoryEvidence]:
        full_query = (
            f"Deal ID: {deal_id}. User question: {query}. "
            f"Requested categories: {', '.join(categories or ['deal history', 'risks', 'stakeholders', 'outcomes'])}. "
            "Return only evidence connected to this deal and distinguish facts from inference."
        )
        started = time.perf_counter()
        try:
            response = await self._client().arecall(
                bank_id=self.settings.hindsight_bank_id,
                query=full_query,
                include_chunks=True,
                max_tokens=6000,
            )
        except Exception as exc:
            logger.warning("hindsight operation=recall duration_ms=%.1f error=%s", (time.perf_counter() - started) * 1000, type(exc).__name__)
            raise HindsightUnavailable() from exc
        duration = (time.perf_counter() - started) * 1000
        items = _get(response, "results", []) or []
        chunks = _get(response, "chunks", {}) or {}
        logger.info("hindsight operation=recall duration_ms=%.1f count=%s", duration, len(items))
        return [self._evidence(item, feature, chunks) for item in items]

    async def reflect_on_deal(
        self, *, deal_id: str, query: str, feature: str
    ) -> tuple[str, list[MemoryEvidence]]:
        prompt = (
            f"Deal ID: {deal_id}. {query}\n"
            "Use only available Hindsight evidence. Separate remembered facts from inference. "
            "Mention uncertainty. Never invent a stakeholder, commitment, date, or outcome. "
            "When possible, cite the remembered evidence in concise language."
        )
        started = time.perf_counter()
        try:
            response = await self._client().areflect(
                bank_id=self.settings.hindsight_bank_id,
                query=prompt,
                include_facts=True,
                budget="mid",
                max_tokens=2500,
            )
        except Exception as exc:
            logger.warning("hindsight operation=reflect duration_ms=%.1f error=%s", (time.perf_counter() - started) * 1000, type(exc).__name__)
            raise HindsightUnavailable() from exc
        duration = (time.perf_counter() - started) * 1000
        based_on = _get(response, "based_on")
        memories = _get(based_on, "memories", []) if based_on else []
        logger.info("hindsight operation=reflect duration_ms=%.1f count=%s", duration, len(memories))
        return str(_get(response, "text") or "No grounded reflection was returned."), [
            self._evidence(item, feature) for item in (memories or [])
        ]

    async def health_check(self) -> dict[str, Any]:
        started = time.perf_counter()
        url = self.settings.hindsight_base_url.rstrip("/") + "/health"
        try:
            async with httpx.AsyncClient(timeout=self.settings.hindsight_timeout_seconds) as http:
                response = await http.get(url)
            response.raise_for_status()
            version = importlib.metadata.version("hindsight-client")
            return {"status": "ok", "client_version": version, "duration_ms": round((time.perf_counter() - started) * 1000, 1)}
        except Exception as exc:
            return {"status": "unavailable", "error": type(exc).__name__, "duration_ms": round((time.perf_counter() - started) * 1000, 1)}

