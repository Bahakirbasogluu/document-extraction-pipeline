"""Data passed between pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel


@dataclass(frozen=True)
class Page:
    number: int
    text: str


@dataclass(frozen=True)
class Segment:
    """Consecutive pages that belong to one document."""

    pages: tuple[Page, ...]

    @property
    def text(self) -> str:
        return "\n".join(p.text for p in self.pages)

    @property
    def page_numbers(self) -> list[int]:
        return [p.number for p in self.pages]


@dataclass(frozen=True)
class Classification:
    doc_type: str
    confidence: float


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class Status(str, Enum):
    ACCEPTED = "accepted"
    NEEDS_REVIEW = "needs_review"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    severity: Severity = Severity.ERROR
    field: str | None = None


@dataclass
class DocumentResult:
    source: str
    pages: list[int]
    doc_type: str
    confidence: float
    status: Status
    data: BaseModel | None = None
    record: dict[str, Any] | None = None
    issues: list[Issue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "pages": self.pages,
            "doc_type": self.doc_type,
            "confidence": round(self.confidence, 3),
            "status": self.status.value,
            "data": self.data.model_dump(mode="json") if self.data else None,
            "record": self.record,
            "issues": [
                {
                    "code": i.code,
                    "severity": i.severity.value,
                    "field": i.field,
                    "message": i.message,
                }
                for i in self.issues
            ],
        }
