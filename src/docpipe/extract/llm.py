from __future__ import annotations

from pydantic import BaseModel

from docpipe.llm import StructuredModel
from docpipe.schemas import SCHEMAS

SYSTEM = (
    "You extract fields from a {doc_type} into the given schema. "
    "Copy values as printed; do not compute, correct or infer them. "
    "Leave a field null when the document does not state it. "
    "Dates are ISO 8601, amounts are plain decimals with a dot, currencies are ISO 4217 codes."
)


class LLMExtractor:
    """Fills the schema of the document type with a structured-output model.

    The instruction not to compute values matters: validation can only catch an
    inconsistent document if the model reports what is printed on it.
    """

    def __init__(self, model: StructuredModel):
        self._model = model

    def extract(self, text: str, doc_type: str) -> BaseModel:
        schema = SCHEMAS[doc_type]
        return self._model.parse(SYSTEM.format(doc_type=doc_type.replace("_", " ")), text, schema)
