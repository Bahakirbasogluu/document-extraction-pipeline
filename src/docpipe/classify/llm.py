from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from docpipe.llm import StructuredModel
from docpipe.models import Classification

SYSTEM = (
    "You classify business documents. Choose the single type that matches the document. "
    "Use 'unknown' when none fits. Do not guess from a single word."
)


class _Answer(BaseModel):
    doc_type: Literal["invoice", "delivery_note", "insurance_policy", "unknown"]
    confidence: float = Field(ge=0, le=1)


class LLMClassifier:
    def __init__(self, model: StructuredModel, max_chars: int = 4000):
        self._model = model
        self._max_chars = max_chars

    def classify(self, text: str) -> Classification:
        answer = self._model.parse(SYSTEM, text[: self._max_chars], _Answer)
        return Classification(answer.doc_type, answer.confidence)
