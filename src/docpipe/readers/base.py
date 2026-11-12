from __future__ import annotations

from pathlib import Path
from typing import Protocol

from docpipe.models import Page


class Reader(Protocol):
    """Turns a file into pages of text. OCR engines plug in here."""

    def read(self, path: Path) -> list[Page]: ...
