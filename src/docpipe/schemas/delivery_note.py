from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class DeliveryItem(BaseModel):
    description: str
    quantity: Decimal
    unit: str


class DeliveryNote(BaseModel):
    note_number: str | None = None
    dispatch_date: date | None = None
    sender_name: str | None = None
    receiver_name: str | None = None
    plate_number: str | None = Field(None, description="Vehicle licence plate")
    total_packages: int | None = None
    items: list[DeliveryItem] = Field(default_factory=list)
