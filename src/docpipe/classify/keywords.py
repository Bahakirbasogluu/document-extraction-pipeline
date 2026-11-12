from __future__ import annotations

import re

from docpipe.models import Classification
from docpipe.parsing import fold
from docpipe.schemas import UNKNOWN

# Title keywords identify the first page of a document; body keywords only add evidence.
TITLES: dict[str, tuple[str, ...]] = {
    "invoice": ("fatura", "invoice"),
    "delivery_note": ("sevk irsaliyesi", "irsaliye", "delivery note", "dispatch note"),
    "insurance_policy": ("sigorta poliçesi", "poliçe", "insurance policy", "policy schedule"),
}
BODY: dict[str, tuple[str, ...]] = {
    "invoice": ("kdv", "vat", "vade", "due date", "ara toplam", "subtotal", "genel toplam"),
    "delivery_note": (
        "plaka",
        "plate",
        "teslim alan",
        "receiver",
        "koli",
        "packages",
        "sevk tarihi",
    ),
    "insurance_policy": (
        "sigortalı",
        "insured",
        "sigortacı",
        "insurer",
        "prim",
        "premium",
        "teminat",
    ),
}


def _count(text: str, words: tuple[str, ...]) -> int:
    return sum(len(re.findall(rf"(?<!\w){re.escape(fold(w))}(?!\w)", text)) for w in words)


class KeywordClassifier:
    """Scores each type by keyword hits. Title hits weigh three times a body hit."""

    def classify(self, text: str) -> Classification:
        low = fold(text)
        scores = {t: 3 * _count(low, TITLES[t]) + _count(low, BODY[t]) for t in TITLES}
        total = sum(scores.values())
        if total == 0:
            return Classification(UNKNOWN, 0.0)
        best = max(scores, key=scores.get)
        return Classification(best, scores[best] / total)


def title_type(page_text: str, head_lines: int = 4) -> str | None:
    """Document type named in the first lines of a page, if any."""
    head = " ".join([ln for ln in fold(page_text).splitlines() if ln.strip()][:head_lines])
    hits = {t: _count(head, words) for t, words in TITLES.items()}
    best = max(hits, key=hits.get)
    return best if hits[best] else None
