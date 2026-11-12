from __future__ import annotations

from pathlib import Path

from docpipe.models import Page


class TextReader:
    """Reads plain-text files in which a form feed separates pages.

    This is the format of the bundled samples and of text dumped by most OCR tools.
    """

    def read(self, path: Path) -> list[Page]:
        raw = Path(path).read_text(encoding="utf-8")
        return [Page(i, chunk.strip("\n")) for i, chunk in enumerate(raw.split("\f"), start=1)]
