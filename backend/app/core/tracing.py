from contextvars import ContextVar
from uuid import uuid4


request_id_context: ContextVar[str] = ContextVar("request_id", default="-")


def new_request_id() -> str:
    value = str(uuid4())
    request_id_context.set(value)
    return value

