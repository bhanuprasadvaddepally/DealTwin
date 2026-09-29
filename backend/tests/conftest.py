import pytest

from app.config import Settings
from app.services.hindsight_service import HindsightService


class FakeRetainResponse:
    operation_id = "op-test-1"


class FakeMemory:
    def __init__(self, text: str, memory_id: str = "memory-1"):
        self.id = memory_id
        self.text = text
        self.score = 0.91


class FakeRecallResponse:
    def __init__(self, texts: list[str]):
        self.results = [FakeMemory(text, f"memory-{index}") for index, text in enumerate(texts, 1)]
        self.chunks = {}


class FakeBasedOn:
    def __init__(self, memories):
        self.memories = memories


class FakeReflectResponse:
    def __init__(self, text: str, memories):
        self.text = text
        self.based_on = FakeBasedOn(memories)


class FakeHindsightClient:
    def __init__(self, memories=None, fail=False):
        self.memories = memories or []
        self.fail = fail
        self.retained = []
        self.recall_queries = []
        self.reflect_queries = []

    async def aretain(self, **kwargs):
        if self.fail:
            raise RuntimeError("offline")
        self.retained.append(kwargs)
        return FakeRetainResponse()

    async def arecall(self, **kwargs):
        if self.fail:
            raise RuntimeError("offline")
        self.recall_queries.append(kwargs["query"])
        return FakeRecallResponse(self.memories)

    async def areflect(self, **kwargs):
        if self.fail:
            raise RuntimeError("offline")
        self.reflect_queries.append(kwargs["query"])
        return FakeReflectResponse("Grounded reflection from test evidence.", [FakeMemory(item) for item in self.memories])


@pytest.fixture
def settings():
    return Settings(hindsight_base_url="http://hindsight.test", hindsight_bank_id="test-bank")


@pytest.fixture
def fake_client():
    return FakeHindsightClient()


@pytest.fixture
def service(settings, fake_client):
    return HindsightService(settings, client=fake_client)

