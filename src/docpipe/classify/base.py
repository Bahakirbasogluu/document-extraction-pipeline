from __future__ import annotations

from typing import Protocol

from docpipe.models import Classification


class Classifier(Protocol):
    def classify(self, text: str) -> Classification: ...
