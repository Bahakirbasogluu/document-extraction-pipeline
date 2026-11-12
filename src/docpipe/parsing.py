"""Parsing of numbers and dates as they appear on Turkish and English documents."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "ocak": 1,
    "şubat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "eylül": 9,
    "ekim": 10,
    "kasım": 11,
    "aralık": 12,
}
_MONTHS = {k.replace("ı", "i"): v for k, v in _MONTHS.items()}
_NUMERIC_DATE_FORMATS = ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y")
_CURRENCY = {
    "₺": "TRY",
    "TL": "TRY",
    "TRY": "TRY",
    "€": "EUR",
    "EUR": "EUR",
    "$": "USD",
    "USD": "USD",
}


def fold(text: str) -> str:
    """Lower-case for matching. Maps İ, I and ı to i so that Turkish capitals compare equal.

    The result has the same length as the input, so match positions carry over.
    """
    return text.replace("İ", "i").replace("ı", "i").lower()


def parse_decimal(raw: str) -> Decimal | None:
    """Parse '1.234,56', '1,234.56', '1234.5' or '20' into a Decimal.

    When both separators occur the last one is the decimal separator. A single
    separator followed by exactly three digits is read as a thousands separator.
    """
    m = re.search(r"-?\d[\d.,]*", raw)
    if not m:
        return None
    s = m.group().rstrip(".,")
    last_dot, last_comma = s.rfind("."), s.rfind(",")
    if last_dot >= 0 and last_comma >= 0:
        dec = "." if last_dot > last_comma else ","
        thousands = "," if dec == "." else "."
        s = s.replace(thousands, "").replace(dec, ".")
    elif last_dot >= 0 or last_comma >= 0:
        sep = "." if last_dot >= 0 else ","
        head, _, tail = s.rpartition(sep)
        if len(tail) == 3 and s.count(sep) >= 1 and head.replace(sep, "").isdigit():
            s = s.replace(sep, "")
        else:
            s = head.replace(sep, "") + "." + tail
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def parse_date(raw: str) -> date | None:
    """Parse numeric dates (12.03.2026, 2026-03-12) and '12 March 2026' / '12 Mart 2026'."""
    text = raw.strip()
    m = re.search(r"\d{4}-\d{2}-\d{2}|\d{1,2}[./-]\d{1,2}[./-]\d{4}", text)
    if m:
        for fmt in _NUMERIC_DATE_FORMATS:
            try:
                return datetime.strptime(m.group(), fmt).date()
            except ValueError:
                continue
    m = re.search(r"(\d{1,2})\s+([^\W\d]+)\s+(\d{4})", text)
    if m and fold(m.group(2)) in _MONTHS:
        try:
            return date(int(m.group(3)), _MONTHS[fold(m.group(2))], int(m.group(1)))
        except ValueError:
            return None
    return None


def parse_currency(raw: str) -> str | None:
    for token in re.findall(r"[₺€$]|[A-Za-z]{2,3}", raw):
        code = _CURRENCY.get(token.upper(), _CURRENCY.get(token))
        if code:
            return code
    return None


def tax_id_check_digit(first_nine: str) -> int:
    """Check digit of a Turkish tax identification number (10 digits)."""
    total = 0
    for i, ch in enumerate(first_nine):
        t = (int(ch) + 9 - i) % 10
        total += 9 if t == 9 else (t * 2 ** (9 - i)) % 9
    return (10 - total % 10) % 10


def is_valid_tax_id(value: str) -> bool:
    return bool(re.fullmatch(r"\d{10}", value)) and tax_id_check_digit(value[:9]) == int(value[9])
