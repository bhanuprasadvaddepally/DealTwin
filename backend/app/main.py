import logging
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .config import Settings, get_settings
from .core.errors import AppError, NotFoundError
from .core.logging import configure_logging
from .core.tracing import new_request_id, request_id_context
from .repositories.db import Database
from .repositories.deal_repository import DealRepository
from .repositories.interaction_repository import InteractionRepository
from .repositories.outcome_repository import OutcomeRepository
from .schemas.deal import Deal, DealCreate
from .schemas.conversation import ConversationMessageCreate, ConversationMessageResponse
from .schemas.intelligence import AfterMemoryRequest, BeforeMemoryResponse, BriefingRequest, ReplayRequest
from .schemas.interaction import InteractionCreate, InteractionResponse
from .schemas.memory import MemoryListResponse
from .schemas.outcome import OutcomeCreate, OutcomeResponse
from .schemas.promise import PromiseDebtResponse
from .schemas.simulation import SimulationRequest, SimulationResponse
from .schemas.stakeholder import StakeholderResponse
from .services.briefing_service import BriefingService
from .services.conversation_service import ConversationService
from .services.hindsight_service import HindsightService
from .services.interaction_service import InteractionService
from .services.outcome_service import OutcomeService
from .services.promise_debt_service import PromiseDebtService
from .services.simulation_service import SimulationService
from .services.stakeholder_service import StakeholderService

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db = Database(settings.database_url)
    db.init()
    app.state.db = db
    app.state.deals = DealRepository(db)
    app.state.interactions = InteractionRepository(db)
    app.state.outcomes = OutcomeRepository(db)
    app.state.hindsight = HindsightService(settings)
    try:
        yield
    finally:
        await app.state.hindsight.close()


app = FastAPI(title="DealTwin", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_origin, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or new_request_id()
    request_id_context.set(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    request_id = request_id_context.get()
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message, "request_id": request_id}})


@app.exception_handler(Exception)
async def unknown_error_handler(request: Request, exc: Exception):
    logger.exception("unhandled error type=%s", type(exc).__name__)
    return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": "Unexpected server error.", "request_id": request_id_context.get()}})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    fields = ", ".join(str(item.get("loc", ["request"])[-1]) for item in exc.errors())
    message = f"Invalid request. Check: {fields}." if fields else "Invalid request."
    return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": message, "request_id": request_id_context.get()}})


def settings() -> Settings:
    return get_settings()


def hindsight(request: Request) -> HindsightService:
    return request.app.state.hindsight


def deal_repo(request: Request) -> DealRepository:
    return request.app.state.deals


def interaction_service(request: Request) -> InteractionService:
    return InteractionService(request.app.state.deals, request.app.state.interactions, request.app.state.hindsight)


def outcome_service(request: Request) -> OutcomeService:
    return OutcomeService(request.app.state.outcomes, request.app.state.hindsight)


@app.get("/health")
async def health(request: Request, app_settings: Settings = Depends(settings)):
    memory = await request.app.state.hindsight.health_check()
    database = "ok"
    try:
        with request.app.state.db.connection() as conn:
            conn.execute("SELECT 1").fetchone()
    except Exception:
        database = "unavailable"
    return {"status": "ok" if memory["status"] == "ok" and database == "ok" else "degraded", "backend": "ok", "database": database, "hindsight": memory, "request_id": request_id_context.get()}


@app.post("/api/deals", response_model=Deal)
async def create_deal(payload: DealCreate, repo: DealRepository = Depends(deal_repo)):
    return repo.create(payload)


@app.get("/api/deals", response_model=list[Deal])
async def list_deals(repo: DealRepository = Depends(deal_repo)):
    return repo.list()


@app.get("/api/deals/{deal_id}", response_model=Deal)
async def get_deal(deal_id: str, repo: DealRepository = Depends(deal_repo)):
    deal = repo.get(deal_id)
    if not deal:
        raise NotFoundError("Deal")
    return deal


@app.delete("/api/deals/{deal_id}")
async def delete_deal(deal_id: str, repo: DealRepository = Depends(deal_repo)):
    if not repo.delete(deal_id):
        raise NotFoundError("Prospect")
    return {"deleted": True, "deal_id": deal_id, "message": "Prospect removed from the DealTwin workspace."}


@app.post("/api/deals/{deal_id}/interactions", response_model=InteractionResponse)
async def add_interaction(deal_id: str, payload: InteractionCreate, service: InteractionService = Depends(interaction_service)):
    return await service.retain(deal_id, payload)


@app.post("/api/deals/{deal_id}/conversation", response_model=ConversationMessageResponse)
async def converse(deal_id: str, payload: ConversationMessageCreate, request: Request):
    return await ConversationService(
        InteractionService(request.app.state.deals, request.app.state.interactions, request.app.state.hindsight),
        request.app.state.hindsight,
    ).respond(deal_id, payload)


@app.get("/api/deals/{deal_id}/memories", response_model=MemoryListResponse)
async def get_memories(deal_id: str, request: Request, query: str = Query(default="What does this deal remember?")):
    if not request.app.state.deals.has_activity(deal_id):
        return MemoryListResponse(query=query, count=0, memories=[])
    memories = await request.app.state.hindsight.recall_deal_memories(deal_id=deal_id, query=query, feature="memory panel")
    return MemoryListResponse(query=query, count=len(memories), memories=memories)


@app.post("/api/deals/{deal_id}/briefing")
async def get_briefing(deal_id: str, payload: BriefingRequest, request: Request):
    return await BriefingService(request.app.state.hindsight).prepare(deal_id, payload.question)


@app.get("/api/deals/{deal_id}/promise-debt", response_model=PromiseDebtResponse)
async def get_promise_debt(deal_id: str, request: Request):
    if not request.app.state.deals.has_activity(deal_id):
        return PromiseDebtResponse(score=0, level="low", explanation="No conversation or interaction has been retained for this prospect yet.", affected_commitments=[], supporting_memories=[], recommended_remediation="Capture the first customer signal before assessing promise risk.")
    return await PromiseDebtService(request.app.state.hindsight).calculate(deal_id)


@app.get("/api/deals/{deal_id}/stakeholders", response_model=StakeholderResponse)
async def get_stakeholders(deal_id: str, request: Request):
    if not request.app.state.deals.has_activity(deal_id):
        return StakeholderResponse(stakeholders=[], recommended_next_contact=None, rationale=None)
    return await StakeholderService(request.app.state.hindsight).list(deal_id)


@app.post("/api/deals/{deal_id}/simulate", response_model=SimulationResponse)
async def simulate(deal_id: str, payload: SimulationRequest, request: Request):
    return await SimulationService(request.app.state.hindsight).simulate(deal_id, payload, request.app.state.deals.has_activity(deal_id))


@app.post("/api/deals/{deal_id}/outcomes", response_model=OutcomeResponse)
async def add_outcome(deal_id: str, payload: OutcomeCreate, service: OutcomeService = Depends(outcome_service)):
    return await service.record(deal_id, payload)


@app.post("/api/demo/before-memory", response_model=BeforeMemoryResponse)
async def before_memory(payload: ReplayRequest):
    question = payload.question
    return BeforeMemoryResponse(
        label="Without Hindsight memory",
        answer=f"A generic preparation for \"{question}\": confirm the agenda, ask about current priorities, listen for objections, and agree on a next step. No deal context was provided to this request.",
        supporting_memories=[],
    )


@app.post("/api/demo/after-memory")
async def after_memory(payload: AfterMemoryRequest, request: Request):
    if not request.app.state.deals.has_activity(payload.deal_id):
        return {
            "label": "With Hindsight memory",
            "answer": "No deal-specific memory is available yet. Capture an interaction before using this replay.",
            "supporting_memories": [],
            "memory_count": 0,
            "reflect_memory_count": 0,
        }
    service = request.app.state.hindsight
    answer, reflected = await service.reflect_on_deal(
        deal_id=payload.deal_id,
        query=f"Prepare a concise next-call briefing for this question: {payload.question}",
        feature="after-memory replay",
    )
    recalled = await service.recall_deal_memories(
        deal_id=payload.deal_id,
        query=payload.question,
        feature="after-memory replay evidence",
    )
    return {
        "label": "With Hindsight memory",
        "answer": answer,
        "supporting_memories": reflected or recalled,
        "memory_count": len(recalled),
        "reflect_memory_count": len(reflected),
    }


@app.post("/api/demo/seed")
async def seed_demo(request: Request):
    repo: DealRepository = request.app.state.deals
    deal = repo.get("acme-logistics") or repo.create(
        DealCreate(name="Acme Logistics expansion", company="Acme Logistics", stage="procurement review", value=240000, decision_date=date(2026, 10, 20)),
        deal_id="acme-logistics",
    )
    service = InteractionService(request.app.state.deals, request.app.state.interactions, request.app.state.hindsight)
    seeded = []
    for content, interaction_date, interaction_type in [
        ("Acme Logistics is evaluating our logistics automation platform. Priya, the CTO, is interested in API integration and deployment time. Rohan, the CFO, thinks the annual price is too high. They are also evaluating CloudRoute. We promised to send the security documentation by Friday.", date(2026, 9, 14), "meeting"),
        ("The technical workshop went well and Priya liked the API demonstration. The operations team still wants a migration plan. Rohan prefers quarterly billing. The security document has not been sent yet. The customer wants a decision by 20 October.", date(2026, 9, 22), "meeting"),
    ]:
        seeded.append(await service.retain(deal.id, InteractionCreate(content=content, interaction_date=interaction_date, interaction_type=interaction_type, source="seeded demo data", participants=[])))
    return {"deal": deal, "seeded": seeded, "message": "Seeded demo interactions through the same Hindsight retain path."}

