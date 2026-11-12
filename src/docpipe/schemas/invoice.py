from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class InvoiceLine(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal


class Invoice(BaseModel):
    """Fields are optional so that a partial extraction still reaches validation,
    where missing required fields are reported one by one."""

    invoice_number: str | None = Field(None, description="Invoice number as printed")
    issue_date: date | None = None
    due_date: date | None = None
    supplier_name: str | None = None
    supplier_tax_id: str | None = Field(None, description="10-digit tax number of the supplier")
    customer_name: str | None = None
    currency: str | None = Field(None, description="ISO 4217 code")
    net_amount: Decimal | None = Field(None, description="Total before VAT")
    vat_rate: Decimal | None = Field(None, description="VAT rate in percent, e.g. 20")
    vat_amount: Decimal | None = None
    gross_amount: Decimal | None = Field(None, description="Total including VAT")
    lines: list[InvoiceLine] = Field(default_factory=list)
