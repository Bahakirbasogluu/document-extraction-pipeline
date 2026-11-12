from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class InsurancePolicy(BaseModel):
    policy_number: str | None = None
    insurer_name: str | None = None
    insured_name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    premium_amount: Decimal | None = None
    currency: str | None = Field(None, description="ISO 4217 code")
