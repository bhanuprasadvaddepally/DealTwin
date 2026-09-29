from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OperationStatus(APIModel):
    status: str
    operation: str
    trace_id: str | None = None
    message: str | None = None


class ErrorBody(APIModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(APIModel):
    error: ErrorBody

