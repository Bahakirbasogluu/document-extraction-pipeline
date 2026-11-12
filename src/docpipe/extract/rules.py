"""Label-based extraction without a model.

It serves as the offline backend and as the baseline an LLM extractor has to beat.
It only finds values that follow a label it knows, on the same line.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from docpipe.parsing import fold, parse_currency, parse_date, parse_decimal
from docpipe.schemas import SCHEMAS

_UNITS = r"adet|pcs|kg|koli|box|palet|pallet|lt"
_INVOICE_LINE = re.compile(
    r"^\s*(\S.*?)\s{2,}(\d+)\s{2,}([\d.,]+)\s{2,}([\d.,]+)\s*$", re.MULTILINE
)
_DELIVERY_LINE = re.compile(
    rf"^\s*(\S.*?)\s{{2,}}(\d+)\s+({_UNITS})\s*$", re.MULTILINE | re.IGNORECASE
)


def _text(v: str) -> str | None:
    return v.strip() or None


def _digits(v: str) -> str | None:
    m = re.search(r"\d{6,}", v.replace(" ", ""))
    return m.group() if m else None


def _percent(v: str):
    m = re.search(r"%\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*%", v)
    return parse_decimal(m.group(1) or m.group(2)) if m else None


def _int(v: str) -> int | None:
    m = re.search(r"\d+", v)
    return int(m.group()) if m else None


Field = tuple[tuple[str, ...], Callable[[str], Any]]

LABELS: dict[str, dict[str, Field]] = {
    "invoice": {
        "invoice_number": (("fatura no", "fatura numarası", "invoice no", "invoice number"), _text),
        "issue_date": (
            ("fatura tarihi", "düzenleme tarihi", "invoice date", "issue date"),
            parse_date,
        ),
        "due_date": (("vade tarihi", "son ödeme tarihi", "due date"), parse_date),
        "supplier_name": (("satıcı", "tedarikçi", "supplier", "seller"), _text),
        "supplier_tax_id": (("vergi no", "vkn", "tax id", "tax number"), _digits),
        "customer_name": (("alıcı", "müşteri", "customer", "bill to"), _text),
        "currency": (("para birimi", "currency"), parse_currency),
        "net_amount": (("ara toplam", "matrah", "subtotal", "net amount"), parse_decimal),
        "vat_amount": (("kdv tutarı", "hesaplanan kdv", "vat amount"), parse_decimal),
        "vat_rate": (("kdv oranı", "vat rate"), _percent),
        "gross_amount": (
            ("genel toplam", "ödenecek tutar", "total due", "grand total"),
            parse_decimal,
        ),
    },
    "delivery_note": {
        "note_number": (("irsaliye no", "delivery note no", "dispatch no"), _text),
        "dispatch_date": (("sevk tarihi", "dispatch date", "delivery date"), parse_date),
        "sender_name": (("gönderen", "sender", "shipper"), _text),
        "receiver_name": (("teslim alan", "alıcı", "receiver", "consignee"), _text),
        "plate_number": (("araç plakası", "plaka", "plate"), _text),
        "total_packages": (("toplam koli", "total packages"), _int),
    },
    "insurance_policy": {
        "policy_number": (("poliçe no", "policy no", "policy number"), _text),
        "insurer_name": (("sigortacı", "sigorta şirketi", "insurer"), _text),
        "insured_name": (("sigortalı", "insured"), _text),
        "start_date": (("başlangıç tarihi", "start date", "effective date"), parse_date),
        "end_date": (("bitiş tarihi", "end date", "expiry date"), parse_date),
        "premium_amount": (
            ("toplam prim", "prim tutarı", "total premium", "premium"),
            parse_decimal,
        ),
        "currency": (("para birimi", "currency"), parse_currency),
    },
}


def _after_label(text: str, folded: str, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        m = re.search(
            rf"^[ \t]*{re.escape(fold(label))}[ \t]*[:.]*[ \t]+(\S.*)$", folded, re.MULTILINE
        )
        if m:
            return text[m.start(1) : m.end(1)]
    return None


class RuleExtractor:
    def extract(self, text: str, doc_type: str) -> BaseModel:
        values: dict[str, Any] = {}
        folded = fold(text)
        for name, (labels, convert) in LABELS[doc_type].items():
            raw = _after_label(text, folded, labels)
            if raw is not None:
                values[name] = convert(raw)
        if doc_type == "invoice":
            values["lines"] = [
                {
                    "description": d.strip(),
                    "quantity": q,
                    "unit_price": parse_decimal(u),
                    "amount": parse_decimal(a),
                }
                for d, q, u, a in _INVOICE_LINE.findall(text)
            ]
        elif doc_type == "delivery_note":
            values["items"] = [
                {"description": d.strip(), "quantity": q, "unit": u.lower()}
                for d, q, u in _DELIVERY_LINE.findall(text)
            ]
        return SCHEMAS[doc_type].model_validate(values)
