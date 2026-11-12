from __future__ import annotations

from pathlib import Path

from docpipe.classify import Classifier, KeywordClassifier
from docpipe.extract import Extractor, RuleExtractor
from docpipe.mapping import to_record
from docpipe.models import DocumentResult, Segment, Severity, Status
from docpipe.readers import Reader, TextReader
from docpipe.schemas import SCHEMAS
from docpipe.split import split_pages
from docpipe.validate import validate


class Pipeline:
    """read -> split -> classify -> extract -> validate -> map.

    Each stage is an interface, so the OCR engine, the classifier and the
    extractor can be swapped without touching the rest.
    """

    def __init__(
        self,
        reader: Reader | None = None,
        classifier: Classifier | None = None,
        extractor: Extractor | None = None,
        min_confidence: float = 0.5,
    ):
        self.reader = reader or TextReader()
        self.classifier = classifier or KeywordClassifier()
        self.extractor = extractor or RuleExtractor()
        self.min_confidence = min_confidence

    def run(self, path: str | Path) -> list[DocumentResult]:
        pages = self.reader.read(Path(path))
        return [self._process(Path(path).name, seg) for seg in split_pages(pages)]

    def _process(self, source: str, segment: Segment) -> DocumentResult:
        cls = self.classifier.classify(segment.text)
        result = DocumentResult(
            source, segment.page_numbers, cls.doc_type, cls.confidence, Status.UNSUPPORTED
        )
        if cls.doc_type not in SCHEMAS or cls.confidence < self.min_confidence:
            return result
        result.data = self.extractor.extract(segment.text, cls.doc_type)
        result.issues = validate(cls.doc_type, result.data)
        if any(i.severity is Severity.ERROR for i in result.issues):
            result.status = Status.NEEDS_REVIEW
        else:
            result.status = Status.ACCEPTED
            result.record = to_record(cls.doc_type, result.data)
        return result
