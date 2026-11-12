"""Business rules that decide whether an extracted document can be posted without review."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from pydantic import BaseModel

from docpipe.models import Issue, Severity
from docpipe.parsing import is_valid_tax_id
from docpipe.schemas import DeliveryNote, InsurancePolicy, Invoice

TOLERANCE = Decimal("0.02")

REQUIRED: dict[str, tuple[str, ...]] = {
    "invoice": (
        "invoice_number",
        "issue_date",
        "supplier_tax_id",
        "currency",
        "net_amount",
        "vat_amount",
        "gross_amount",
    ),
    "delivery_note": ("note_number", "dispatch_date", "sender_name", "receiver_name"),
    "insurance_policy": (
        "policy_number",
        "insured_name",
        "start_date",
        "end_date",
        "premium_amount",
    ),
}


def _close(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) <= TOLERANCE


def _invoice(d: Invoice) -> list[Issue]:
    issues: list[Issue] = []
    if None not in (d.net_amount, d.vat_amount, d.gross_amount) and not _close(
        d.net_amount + d.vat_amount, d.gross_amount
    ):
        issues.append(
            Issue(
                "totals_mismatch",
                f"net {d.net_amount} + VAT {d.vat_amount} is not gross {d.gross_amount}",
                field="gross_amount",
            )
        )
    if None not in (d.net_amount, d.vat_rate, d.vat_amount) and not _close(
        d.net_amount * d.vat_rate / 100, d.vat_amount
    ):
        issues.append(
            Issue(
                "vat_mismatch",
                f"{d.vat_rate}% of {d.net_amount} is not {d.vat_amount}",
                field="vat_amount",
            )
        )
    if (
        d.lines
        and d.net_amount is not None
        and not _close(sum(ln.amount for ln in d.lines), d.net_amount)
    ):
        issues.append(
            Issue("lines_mismatch", "line amounts do not add up to the net amount", field="lines")
        )
    for i, ln in enumerate(d.lines):
        if not _close(ln.quantity * ln.unit_price, ln.amount):
            issues.append(
                Issue(
                    "line_amount_mismatch",
                    f"line {i + 1}: quantity x unit price is not the amount",
                    field=f"lines[{i}]",
                )
            )
    if d.issue_date and d.due_date and d.due_date < d.issue_date:
        issues.append(
            Issue("due_before_issue", "due date is earlier than the issue date", field="due_date")
        )
    if d.supplier_tax_id and not is_valid_tax_id(d.supplier_tax_id):
        issues.append(
            Issue(
                "invalid_tax_id",
                "supplier tax number fails its check digit",
                field="supplier_tax_id",
            )
        )
    if not d.lines:
        issues.append(Issue("no_lines", "no line items were read", Severity.WARNING, "lines"))
    return issues


def _delivery_note(d: DeliveryNote) -> list[Issue]:
    issues: list[Issue] = []
    if not d.items:
        issues.append(Issue("no_items", "no items were read", field="items"))
    if d.plate_number is None:
        issues.append(
            Issue("missing_plate", "vehicle plate is not stated", Severity.WARNING, "plate_number")
        )
    return issues


def _insurance_policy(d: InsurancePolicy) -> list[Issue]:
    issues: list[Issue] = []
    if d.start_date and d.end_date and d.end_date <= d.start_date:
        issues.append(
            Issue("invalid_period", "end date is not after the start date", field="end_date")
        )
    if d.premium_amount is not None and d.premium_amount <= 0:
        issues.append(Issue("invalid_premium", "premium is not positive", field="premium_amount"))
    return issues


RULES: dict[str, Callable[[BaseModel], list[Issue]]] = {
    "invoice": _invoice,
    "delivery_note": _delivery_note,
    "insurance_policy": _insurance_policy,
}


def validate(doc_type: str, data: BaseModel) -> list[Issue]:
    issues = [
        Issue("missing_field", f"{name} was not found", field=name)
        for name in REQUIRED[doc_type]
        if getattr(data, name) is None
    ]
    return issues + RULES[doc_type](data)
