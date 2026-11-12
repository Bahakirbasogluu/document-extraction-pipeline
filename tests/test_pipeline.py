from decimal import Decimal
from pathlib import Path

from docpipe import Pipeline, Status
from docpipe.classify import LLMClassifier
from docpipe.extract import LLMExtractor
from docpipe.models import Page
from docpipe.parsing import tax_id_check_digit
from docpipe.schemas import Invoice
from docpipe.split import split_pages
from docpipe.validate import validate

TAX_ID = "123456789" + str(tax_id_check_digit("123456789"))
BAD_TAX_ID = "123456789" + str((tax_id_check_digit("123456789") + 1) % 10)

INVOICE = f"""FATURA

Satıcı: Kuzey Ambalaj Sanayi A.Ş.
Vergi No: {TAX_ID}
Alıcı: Ege Lojistik A.Ş.
Fatura No: FTR2026000123
Fatura Tarihi: 12.03.2026
Vade Tarihi: 11.04.2026
Para Birimi: TRY

Açıklama                        Miktar   Birim Fiyat           Tutar
Koli bandı 45 mm                    10        100,00        1.000,00
İş eldiveni                          5         50,00          250,00

Ara Toplam: 1.250,00
KDV Oranı: %20
KDV Tutarı: 250,00
Genel Toplam: 1.500,00
"""

NOTE = """SEVK İRSALİYESİ

İrsaliye No: IRS123456
Sevk Tarihi: 2026-03-12
Gönderen: Kuzey Ambalaj Sanayi A.Ş.
Teslim Alan: Ege Lojistik A.Ş.
Plaka: 34 ABC 123

Malzeme                         Miktar
Koli bandı 45 mm                10 koli
"""


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "doc.txt"
    path.write_text(text, encoding="utf-8")
    return path


def test_clean_invoice_is_accepted_and_mapped(tmp_path):
    [result] = Pipeline().run(write(tmp_path, INVOICE))
    assert result.doc_type == "invoice"
    assert result.status is Status.ACCEPTED
    assert result.data.gross_amount == Decimal("1500.00")
    assert [ln.amount for ln in result.data.lines] == [Decimal("1000.00"), Decimal("250.00")]
    assert result.record["tax_code"] == "V20"
    assert result.record["vendor_tax_id"] == TAX_ID


def test_inconsistent_totals_go_to_review(tmp_path):
    [result] = Pipeline().run(
        write(tmp_path, INVOICE.replace("Genel Toplam: 1.500,00", "Genel Toplam: 1.600,00"))
    )
    assert result.status is Status.NEEDS_REVIEW
    assert result.record is None
    assert "totals_mismatch" in {i.code for i in result.issues}


def test_missing_required_field_is_reported(tmp_path):
    [result] = Pipeline().run(write(tmp_path, INVOICE.replace("Fatura No: FTR2026000123\n", "")))
    assert ("missing_field", "invoice_number") in {(i.code, i.field) for i in result.issues}


def test_bundle_is_split_by_title_pages(tmp_path):
    second_page = (
        "Sayfa 2 / 2\n\nEtiket rulosu                        1         10,00           10,00"
    )
    results = Pipeline().run(write(tmp_path, NOTE + "\f" + INVOICE + "\f" + second_page))
    assert [(r.doc_type, r.pages) for r in results] == [("delivery_note", [1]), ("invoice", [2, 3])]


def test_split_skips_blank_pages():
    segments = split_pages([Page(1, "FATURA\nx"), Page(2, "  "), Page(3, "devam")])
    assert [s.page_numbers for s in segments] == [[1, 3]]


def test_unrelated_text_is_unsupported(tmp_path):
    [result] = Pipeline().run(write(tmp_path, "Toplantı notu\nRaf düzeni gelecek ay yenilenecek."))
    assert result.status is Status.UNSUPPORTED
    assert result.data is None


def test_validation_flags_bad_tax_id_and_dates():
    data = Invoice.model_validate(
        {
            "invoice_number": "A1",
            "issue_date": "2026-03-12",
            "due_date": "2026-03-01",
            "supplier_tax_id": BAD_TAX_ID,
            "currency": "TRY",
            "net_amount": "100",
            "vat_rate": "20",
            "vat_amount": "20",
            "gross_amount": "120",
        }
    )
    codes = {i.code for i in validate("invoice", data)}
    assert {"due_before_issue", "invalid_tax_id"} <= codes
    assert "totals_mismatch" not in codes


class FakeModel:
    """Stands in for a structured-output model and records what it was asked."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def parse(self, system, user, schema):
        self.calls.append((system, schema.__name__))
        return schema.model_validate(self.answers[schema.__name__])


def test_llm_backend_uses_the_schema_of_the_classified_type(tmp_path):
    model = FakeModel(
        {
            "_Answer": {"doc_type": "invoice", "confidence": 0.93},
            "Invoice": {
                "invoice_number": "X-1",
                "issue_date": "2026-03-12",
                "supplier_tax_id": TAX_ID,
                "currency": "EUR",
                "net_amount": "100",
                "vat_rate": "20",
                "vat_amount": "20",
                "gross_amount": "120",
                "lines": [
                    {"description": "a", "quantity": "1", "unit_price": "100", "amount": "100"}
                ],
            },
        }
    )
    pipeline = Pipeline(classifier=LLMClassifier(model), extractor=LLMExtractor(model))
    [result] = pipeline.run(write(tmp_path, "Rechnung Nr. X-1 ..."))
    assert [name for _, name in model.calls] == ["_Answer", "Invoice"]
    assert result.status is Status.ACCEPTED
    assert result.record["reference"] == "X-1"
