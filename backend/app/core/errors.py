from dataclasses import dataclass


@dataclass
class AppError(Exception):
    code: str
    message: str
    status_code: int = 500


class HindsightUnavailable(AppError):
    def __init__(self, detail: str | None = None):
        suffix = f" {detail}" if detail else ""
        super().__init__(
            "HINDSIGHT_UNAVAILABLE",
            f"Hindsight is unavailable. Start the Hindsight server and retry.{suffix}",
            503,
        )


class NotFoundError(AppError):
    def __init__(self, resource: str):
        super().__init__("NOT_FOUND", f"{resource} was not found.", 404)

