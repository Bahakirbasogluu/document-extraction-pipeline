"""Maps a validated document to the record a downstream system expects.

The target here is a generic accounting or logistics payload. In a real
integration this is the only module that knows the field names of the ERP.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from docpipe.schemas import DeliveryNote, InsurancePolicy, Invoice

TAX_CODES = {"0": "V0", "1": "V1", "10": "V10", "20": "V20"}


def _invoice(d: Invoice) -> dict[str, Any]:
    rate = None if d.vat_rate is None else format(d.vat_rate.normalize(), "f")
    return {
        "record_type": "vendor_invoice",
        "reference": d.invoice_number,
        "vendor_tax_id": d.supplier_tax_id,
        "document_date": d.issue_date.isoformat(),
        "due_date": d.due_date.isoformat() if d.due_date else None,
        "currency": d.currency,
        "gross_amount": str(d.gross_amount),
        "tax_amount": str(d.vat_amount),
        "tax_code": TAX_CODES.get(rate),
        "items": [{"text": ln.description, "amount": str(ln.amount)} for ln in d.lines],
    }


def _delivery_note(d: DeliveryNote) -> dict[str, Any]:
    return {
        "record_type": "goods_movement",
        "reference": d.note_number,
        "movement_date": d.dispatch_date.isoformat(),
        "ship_from": d.sender_name,
        "ship_to": d.receiver_name,
        "vehicle": d.plate_number,
        "items": [
            {"text": i.description, "quantity": str(i.quantity), "unit": i.unit} for i in d.items
        ],
    }


def _insurance_policy(d: InsurancePolicy) -> dict[str, Any]:
    return {
        "record_type": "insurance_contract",
        "reference": d.policy_number,
        "partner": d.insurer_name,
        "insured": d.insured_name,
        "valid_from": d.start_date.isoformat(),
        "valid_to": d.end_date.isoformat(),
        "premium": str(d.premium_amount),
        "currency": d.currency,
    }


MAPPERS: dict[str, Callable[[BaseModel], dict[str, Any]]] = {
    "invoice": _invoice,
    "delivery_note": _delivery_note,
    "insurance_policy": _insurance_policy,
}


def to_record(doc_type: str, data: BaseModel) -> dict[str, Any]:
    return MAPPERS[doc_type](data)
