"""Document types and their target schemas.

Adding a document type means adding a schema here, keywords for the classifier,
rules in ``docpipe.validate`` and a mapper in ``docpipe.mapping``.
"""

from __future__ import annotations

from pydantic import BaseModel

from docpipe.schemas.delivery_note import DeliveryNote
from docpipe.schemas.insurance_policy import InsurancePolicy
from docpipe.schemas.invoice import Invoice

UNKNOWN = "unknown"

SCHEMAS: dict[str, type[BaseModel]] = {
    "invoice": Invoice,
    "delivery_note": DeliveryNote,
    "insurance_policy": InsurancePolicy,
}

__all__ = ["SCHEMAS", "UNKNOWN", "DeliveryNote", "InsurancePolicy", "Invoice"]
