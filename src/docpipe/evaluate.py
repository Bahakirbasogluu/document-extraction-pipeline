"""Scores pipeline output against labelled documents."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from docpipe.models import DocumentResult, Status
from docpipe.pipeline import Pipeline
from docpipe.schemas import UNKNOWN


def _norm(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_norm(v) for v in value]
    if isinstance(value, dict):
        return {k: _norm(v) for k, v in value.items()}
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value)).normalize()
    text = " ".join(str(value).split())
    try:
        return Decimal(text).normalize()
    except InvalidOperation:
        return text.casefold()


@dataclass
class Report:
    files: int = 0
    files_split_correctly: int = 0
    documents: int = 0
    documents_typed_correctly: int = 0
    fields: dict[str, list[int]] = field(default_factory=lambda: defaultdict(lambda: [0, 0]))
    review: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def summary(self) -> dict[str, Any]:
        by_type: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for key, (hit, total) in self.fields.items():
            by_type[key.split(".")[0]][0] += hit
            by_type[key.split(".")[0]][1] += total
        hit = sum(h for h, _ in self.fields.values())
        total = sum(t for _, t in self.fields.values())
        r = self.review
        return {
            "files": self.files,
            "files_split_correctly": self.files_split_correctly,
            "documents": self.documents,
            "classification_accuracy": _ratio(self.documents_typed_correctly, self.documents),
            "field_accuracy": _ratio(hit, total),
            "field_accuracy_by_type": {t: _ratio(h, n) for t, (h, n) in sorted(by_type.items())},
            "field_accuracy_by_field": {
                k: _ratio(h, n) for k, (h, n) in sorted(self.fields.items())
            },
            "review": {
                "faulty_documents": r["faulty"],
                "faulty_sent_to_review": r["faulty_reviewed"],
                "faulty_with_the_fault_named": r["faulty_named"],
                "clean_documents": r["clean"],
                "clean_accepted": r["clean_accepted"],
            },
        }


def _ratio(a: int, b: int) -> float | None:
    return round(a / b, 4) if b else None


def score(report: Report, predicted: list[DocumentResult], gold: list[dict[str, Any]]) -> None:
    report.files += 1
    report.files_split_correctly += len(predicted) == len(gold)
    for i, want in enumerate(gold):
        got = predicted[i] if i < len(predicted) else None
        report.documents += 1
        doc_type = want["type"]
        typed = got is not None and (
            got.doc_type == doc_type or (doc_type == UNKNOWN and got.status is Status.UNSUPPORTED)
        )
        report.documents_typed_correctly += typed
        if doc_type == UNKNOWN:
            continue
        data = got.data.model_dump() if typed and got.data is not None else {}
        for name, value in want["fields"].items():
            cell = report.fields[f"{doc_type}.{name}"]
            cell[1] += 1
            cell[0] += _norm(data.get(name)) == _norm(value)
        reviewed = got is None or got.status is not Status.ACCEPTED
        if want.get("expected_errors"):
            report.review["faulty"] += 1
            report.review["faulty_reviewed"] += reviewed
            codes = {i.code for i in got.issues} if got is not None else set()
            report.review["faulty_named"] += set(want["expected_errors"]) <= codes
        else:
            report.review["clean"] += 1
            report.review["clean_accepted"] += not reviewed


def evaluate(pipeline: Pipeline, docs_dir: str | Path, gold_dir: str | Path) -> Report:
    report = Report()
    for gold_file in sorted(Path(gold_dir).glob("*.json")):
        gold = json.loads(gold_file.read_text(encoding="utf-8"))
        predicted = pipeline.run(Path(docs_dir) / gold["file"])
        score(report, predicted, gold["documents"])
    return report
