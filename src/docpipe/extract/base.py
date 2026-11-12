from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class Extractor(Protocol):
    def extract(self, text: str, doc_type: str) -> BaseModel: ...
