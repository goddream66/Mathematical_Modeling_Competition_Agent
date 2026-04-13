from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppError(Exception):
    code: str
    message: str
    stage: str
    detail: dict[str, Any] = field(default_factory=dict)
    status_code: int = 400

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def to_payload(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "stage": self.stage,
            "detail": self.detail,
        }


def bad_request(code: str, message: str, *, stage: str, **detail: Any) -> AppError:
    return AppError(code=code, message=message, stage=stage, detail=detail, status_code=400)


def not_found(code: str, message: str, *, stage: str, **detail: Any) -> AppError:
    return AppError(code=code, message=message, stage=stage, detail=detail, status_code=404)


def internal_error(code: str, message: str, *, stage: str, **detail: Any) -> AppError:
    return AppError(code=code, message=message, stage=stage, detail=detail, status_code=500)
