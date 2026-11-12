from datetime import date
from decimal import Decimal

import pytest

from docpipe.parsing import (
    fold,
    is_valid_tax_id,
    parse_currency,
    parse_date,
    parse_decimal,
    tax_id_check_digit,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.234,56", "1234.56"),
        ("1,234.56", "1234.56"),
        ("12.500,00 TL", "12500.00"),
        ("1.234", "1234"),
        ("1,5", "1.5"),
        ("0.75", "0.75"),
        ("20", "20"),
        ("1.234.567,89", "1234567.89"),
    ],
)
def test_parse_decimal(raw, expected):
    assert parse_decimal(raw) == Decimal(expected)


def test_parse_decimal_without_number():
    assert parse_decimal("n/a") is None


@pytest.mark.parametrize(
    "raw",
    ["12.03.2026", "12/03/2026", "2026-03-12", "12 Mart 2026", "12 March 2026", "12 MART 2026"],
)
def test_parse_date(raw):
    assert parse_date(raw) == date(2026, 3, 12)


def test_parse_date_turkish_month_with_dotless_i():
    assert parse_date("3 Kasım 2026") == date(2026, 11, 3)
    assert parse_date("3 KASIM 2026") == date(2026, 11, 3)


def test_parse_date_rejects_impossible_day():
    assert parse_date("31 Şubat 2026") is None


def test_parse_currency():
    assert parse_currency("1.000,00 TL") == "TRY"
    assert parse_currency("EUR") == "EUR"
    assert parse_currency("12,00") is None


def test_fold_keeps_length_and_matches_turkish_capitals():
    assert fold("SEVK İRSALİYESİ") == "sevk irsaliyesi"
    assert fold("SATICI") == fold("Satıcı")
    assert len(fold("İIıi")) == 4


def test_tax_id_check_digit_round_trip():
    nine = "123456789"
    good = nine + str(tax_id_check_digit(nine))
    assert is_valid_tax_id(good)
    assert not is_valid_tax_id(nine + str((int(good[-1]) + 1) % 10))
    assert not is_valid_tax_id("12345")
