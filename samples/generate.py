"""Generates the synthetic sample documents and their labels.

    python samples/generate.py

Everything is invented: company names, tax numbers, plates and amounts. The
documents vary in language, label wording, number and date formats and layout.
Some use labels the rule-based extractor does not know or put the value on the
next line, and some carry deliberate faults (totals that do not add up, a due
date before the issue date, a tax number with a wrong check digit) for the
validation step to catch.
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from docpipe.parsing import tax_id_check_digit

HERE = Path(__file__).parent
rng = random.Random(7)

COMPANIES = [
    "Kuzey Ambalaj Sanayi A.Ş.",
    "Marmara Kimya Ltd. Şti.",
    "Ege Lojistik A.Ş.",
    "Anadolu Yedek Parça Ltd. Şti.",
    "Toros Enerji Hizmetleri A.Ş.",
    "Boğaziçi Tekstil A.Ş.",
    "Northwind Supplies Ltd.",
    "Harbor Freight Partners Ltd.",
    "Bluefield Components GmbH",
    "Meridian Industrial Services Ltd.",
]
INSURERS = ["Yıldız Sigorta A.Ş.", "Atlas Sigorta A.Ş.", "Crown Mutual Insurance Ltd."]
PRODUCTS_TR = [
    "Oluklu mukavva kutu",
    "Streç film 50 cm",
    "Ahşap palet 80x120",
    "Endüstriyel solvent 20 lt",
    "Rulman 6204",
    "Hidrolik hortum 2 m",
    "Koli bandı 45 mm",
    "İş eldiveni",
    "Filtre kartuşu",
    "Etiket rulosu",
]
PRODUCTS_EN = [
    "Corrugated box",
    "Stretch film 50 cm",
    "Wooden pallet 80x120",
    "Industrial solvent 20 l",
    "Bearing 6204",
    "Hydraulic hose 2 m",
    "Packing tape 45 mm",
    "Work gloves",
    "Filter cartridge",
    "Label roll",
]
MONTHS = {
    "tr": [
        "Ocak",
        "Şubat",
        "Mart",
        "Nisan",
        "Mayıs",
        "Haziran",
        "Temmuz",
        "Ağustos",
        "Eylül",
        "Ekim",
        "Kasım",
        "Aralık",
    ],
    "en": [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ],
}

# (label, known to the rule extractor)
L = {
    "tr": {
        "invoice_number": [("Fatura No", 1), ("Fatura Numarası", 1), ("Belge No", 0)],
        "issue_date": [("Fatura Tarihi", 1), ("Düzenleme Tarihi", 1)],
        "due_date": [("Vade Tarihi", 1), ("Son Ödeme Tarihi", 1)],
        "supplier_name": [("Satıcı", 1), ("Tedarikçi", 1)],
        "supplier_tax_id": [("Vergi No", 1), ("VKN", 1)],
        "customer_name": [("Alıcı", 1), ("Müşteri", 1), ("Sayın", 0)],
        "net_amount": [("Ara Toplam", 1), ("Matrah", 1)],
        "vat_amount": [("KDV Tutarı", 1), ("Hesaplanan KDV", 1)],
        "vat_rate": [("KDV Oranı", 1)],
        "gross_amount": [("Genel Toplam", 1), ("Ödenecek Tutar", 1), ("Toplam Tutar", 0)],
        "currency": [("Para Birimi", 1)],
        "note_number": [("İrsaliye No", 1), ("Evrak No", 0)],
        "dispatch_date": [("Sevk Tarihi", 1)],
        "sender_name": [("Gönderen", 1)],
        "receiver_name": [("Teslim Alan", 1), ("Alıcı", 1)],
        "plate_number": [("Araç Plakası", 1), ("Plaka", 1)],
        "total_packages": [("Toplam Koli", 1)],
        "policy_number": [("Poliçe No", 1), ("Sözleşme No", 0)],
        "insurer_name": [("Sigortacı", 1), ("Sigorta Şirketi", 1)],
        "insured_name": [("Sigortalı", 1)],
        "start_date": [("Başlangıç Tarihi", 1)],
        "end_date": [("Bitiş Tarihi", 1)],
        "premium_amount": [("Toplam Prim", 1), ("Prim Tutarı", 1)],
    },
    "en": {
        "invoice_number": [("Invoice No", 1), ("Invoice Number", 1), ("Reference", 0)],
        "issue_date": [("Invoice Date", 1), ("Issue Date", 1)],
        "due_date": [("Due Date", 1)],
        "supplier_name": [("Supplier", 1), ("Seller", 1)],
        "supplier_tax_id": [("Tax ID", 1), ("Tax Number", 1)],
        "customer_name": [("Customer", 1), ("Bill To", 1)],
        "net_amount": [("Subtotal", 1), ("Net Amount", 1)],
        "vat_amount": [("VAT Amount", 1)],
        "vat_rate": [("VAT Rate", 1)],
        "gross_amount": [("Grand Total", 1), ("Total Due", 1), ("Amount Payable", 0)],
        "currency": [("Currency", 1)],
        "note_number": [("Delivery Note No", 1), ("Dispatch No", 1)],
        "dispatch_date": [("Dispatch Date", 1), ("Delivery Date", 1)],
        "sender_name": [("Sender", 1), ("Shipper", 1)],
        "receiver_name": [("Receiver", 1), ("Consignee", 1)],
        "plate_number": [("Plate", 1)],
        "total_packages": [("Total Packages", 1)],
        "policy_number": [("Policy No", 1), ("Policy Number", 1)],
        "insurer_name": [("Insurer", 1)],
        "insured_name": [("Insured", 1)],
        "start_date": [("Start Date", 1), ("Effective Date", 1)],
        "end_date": [("End Date", 1), ("Expiry Date", 1)],
        "premium_amount": [("Total Premium", 1), ("Premium", 1)],
    },
}


def label(lang: str, name: str) -> str:
    options = L[lang][name]
    known = [o for o, k in options if k]
    unknown = [o for o, k in options if not k]
    return rng.choice(unknown) if unknown and rng.random() < 0.15 else rng.choice(known)


def row(lang: str, name: str, value: str) -> str:
    lab = label(lang, name)
    style = rng.random()
    if style < 0.08:
        return f"{lab}\n{value}"
    if style < 0.30:
        return f"{lab:<22}{value}"
    return f"{lab}: {value}"


def money(x: Decimal, lang: str) -> str:
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") if lang == "tr" else s


def fmt_date(d: date, lang: str) -> str:
    k = rng.randrange(4)
    if k == 0:
        return d.isoformat()
    if k == 1:
        return f"{d.day} {MONTHS[lang][d.month - 1]} {d.year}"
    return d.strftime("%d.%m.%Y" if lang == "tr" else "%d/%m/%Y")


def tax_id(valid: bool = True) -> str:
    nine = "".join(rng.choice("0123456789") for _ in range(9))
    check = tax_id_check_digit(nine)
    return nine + str(check if valid else (check + 3) % 10)


def day() -> date:
    return date(2026, 1, 5) + timedelta(days=rng.randrange(280))


def invoice(lang: str, n_lines: int, fault: str | None = None) -> tuple[str, dict]:
    products = PRODUCTS_TR if lang == "tr" else PRODUCTS_EN
    currency = "TRY" if lang == "tr" else rng.choice(["EUR", "USD"])
    supplier, customer = rng.sample(COMPANIES, 2)
    lines = []
    for desc in rng.sample(products, n_lines):
        qty = rng.randrange(1, 40)
        price = Decimal(rng.randrange(500, 90000)) / 100
        lines.append(
            {
                "description": desc,
                "quantity": str(qty),
                "unit_price": str(price),
                "amount": str(qty * price),
            }
        )
    net = sum(Decimal(ln["amount"]) for ln in lines)
    rate = Decimal(rng.choice([10, 20]))
    vat = (net * rate / 100).quantize(Decimal("0.01"))
    gross = net + vat
    issued = day()
    due = issued + timedelta(days=rng.choice([15, 30, 45]))
    tid = tax_id(valid=fault != "invalid_tax_id")
    if fault == "totals_mismatch":
        gross += Decimal(rng.choice([10, 100, 1000]))
    if fault == "due_before_issue":
        due = issued - timedelta(days=10)
    number = f"{rng.choice(['FTR', 'INV', 'A'])}{rng.randrange(2026000001, 2026999999)}"
    f = {
        "invoice_number": number,
        "issue_date": issued.isoformat(),
        "due_date": due.isoformat(),
        "supplier_name": supplier,
        "supplier_tax_id": tid,
        "customer_name": customer,
        "currency": currency,
        "net_amount": str(net),
        "vat_rate": str(rate),
        "vat_amount": str(vat),
        "gross_amount": str(gross),
        "lines": lines,
    }

    head = [
        "FATURA" if lang == "tr" else "INVOICE",
        "",
        row(lang, "supplier_name", supplier),
        row(lang, "supplier_tax_id", tid),
        row(lang, "customer_name", customer),
        "",
        row(lang, "invoice_number", number),
        row(lang, "issue_date", fmt_date(issued, lang)),
        row(lang, "due_date", fmt_date(due, lang)),
    ]
    explicit_currency = rng.random() < 0.85
    if explicit_currency:
        head.append(row(lang, "currency", currency))
    suffix = "" if explicit_currency else (" TL" if currency == "TRY" else f" {currency}")
    cols = (
        ("Açıklama", "Miktar", "Birim Fiyat", "Tutar")
        if lang == "tr"
        else ("Description", "Qty", "Unit Price", "Amount")
    )
    table = [f"{cols[0]:<30}  {cols[1]:>6}  {cols[2]:>12}  {cols[3]:>14}"]
    body = [
        f"{ln['description']:<30}  {ln['quantity']:>6}  {money(Decimal(ln['unit_price']), lang):>12}  {money(Decimal(ln['amount']), lang):>14}"
        for ln in lines
    ]
    totals = ["", row(lang, "net_amount", money(net, lang) + suffix)]
    if rng.random() < 0.85:
        totals += [
            row(lang, "vat_rate", f"%{rate}" if lang == "tr" else f"{rate}%"),
            row(lang, "vat_amount", money(vat, lang) + suffix),
        ]
    else:
        totals.append(
            f"KDV (%{rate}): {money(vat, lang)}{suffix}"
            if lang == "tr"
            else f"VAT ({rate}%): {money(vat, lang)}{suffix}"
        )
    totals.append(row(lang, "gross_amount", money(gross, lang) + suffix))
    if n_lines > 6:
        page2 = ["Sayfa 2 / 2" if lang == "tr" else "Page 2 of 2", ""] + body[6:] + totals
        text = "\n".join(head + [""] + table + body[:6]) + "\f" + "\n".join(page2)
    else:
        text = "\n".join(head + [""] + table + body + totals)
    return text, {"type": "invoice", "fields": f, "expected_errors": [fault] if fault else []}


def delivery_note(lang: str) -> tuple[str, dict]:
    products = PRODUCTS_TR if lang == "tr" else PRODUCTS_EN
    units = ["adet", "koli", "palet", "kg"] if lang == "tr" else ["pcs", "box", "pallet", "kg"]
    sender, receiver = rng.sample(COMPANIES, 2)
    items = [
        {"description": d, "quantity": str(rng.randrange(1, 60)), "unit": rng.choice(units)}
        for d in rng.sample(products, rng.randrange(2, 6))
    ]
    number = f"IRS{rng.randrange(100000, 999999)}"
    sent = day()
    plate = f"{rng.randrange(1, 82):02d} {''.join(rng.choice('ABCDEFGHKLMNPRSTUVYZ') for _ in range(3))} {rng.randrange(10, 999)}"
    packages = rng.randrange(2, 80)
    f = {
        "note_number": number,
        "dispatch_date": sent.isoformat(),
        "sender_name": sender,
        "receiver_name": receiver,
        "plate_number": plate,
        "total_packages": packages,
        "items": items,
    }
    cols = ("Malzeme", "Miktar") if lang == "tr" else ("Item", "Quantity")
    out = [
        "SEVK İRSALİYESİ" if lang == "tr" else "DELIVERY NOTE",
        "",
        row(lang, "note_number", number),
        row(lang, "dispatch_date", fmt_date(sent, lang)),
        row(lang, "sender_name", sender),
        row(lang, "receiver_name", receiver),
        row(lang, "plate_number", plate),
        "",
        f"{cols[0]:<30}  {cols[1]}",
    ]
    out += [f"{i['description']:<30}  {i['quantity']} {i['unit']}" for i in items]
    out += [
        "",
        row(lang, "total_packages", str(packages)),
        "Malzeme eksiksiz teslim alınmıştır." if lang == "tr" else "Goods received in full.",
    ]
    return "\n".join(out), {"type": "delivery_note", "fields": f, "expected_errors": []}


def policy(lang: str, fault: str | None = None) -> tuple[str, dict]:
    insurer, insured = rng.choice(INSURERS), rng.choice(COMPANIES)
    start = day()
    end = start - timedelta(days=30) if fault == "invalid_period" else start + timedelta(days=365)
    premium = Decimal(rng.randrange(150000, 9000000)) / 100
    currency = "TRY" if lang == "tr" else "EUR"
    number = f"POL-{rng.randrange(10000000, 99999999)}"
    f = {
        "policy_number": number,
        "insurer_name": insurer,
        "insured_name": insured,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "premium_amount": str(premium),
        "currency": currency,
    }
    out = [
        "SİGORTA POLİÇESİ" if lang == "tr" else "INSURANCE POLICY",
        "",
        row(lang, "policy_number", number),
        row(lang, "insurer_name", insurer),
        row(lang, "insured_name", insured),
        row(lang, "start_date", fmt_date(start, lang)),
        row(lang, "end_date", fmt_date(end, lang)),
        "",
        (
            "Teminat: Yangın, hırsızlık ve nakliye rizikoları poliçe genel şartlarına göre teminat altındadır."
            if lang == "tr"
            else "Cover: fire, theft and transit risks are covered under the general conditions."
        ),
        "",
        row(lang, "premium_amount", money(premium, lang)),
        row(lang, "currency", currency),
    ]
    return "\n".join(out), {
        "type": "insurance_policy",
        "fields": f,
        "expected_errors": [fault] if fault else [],
    }


OTHER = [
    "TOPLANTI NOTU\n\nKonu: Depo yerleşim planı\nKatılımcılar: Operasyon, Satın Alma\n\nRaf düzeni gelecek ay yenilenecek. Sayım tarihi ayrıca duyurulacak.",
    "MEETING MINUTES\n\nSubject: warehouse layout\nAttendees: operations, procurement\n\nThe racking will be renewed next month. The stock count date will follow.",
    "DEKONT\n\nİşlem Tarihi: 14.04.2026\nGönderen Hesap: Kuzey Ambalaj Sanayi A.Ş.\nAlıcı Hesap: Ege Lojistik A.Ş.\nTutar: 12.500,00 TL\nAçıklama: Nisan ayı ödemesi",
    "ÖDEME HATIRLATMA\n\nSayın yetkili,\nA2026004417 numaralı fatura için vade tarihi geçmiştir. Fatura tutarı KDV dahil 48.200,00 TL olup ödemenin bu hafta içinde yapılmasını rica ederiz.",
]


def main() -> None:
    docs, gold = HERE / "docs", HERE / "gold"
    for d in (docs, gold):
        d.mkdir(exist_ok=True)
        for old in d.iterdir():
            old.unlink()
    files: list[tuple[str, list[tuple[str, dict]]]] = []
    faults = {
        2: "totals_mismatch",
        5: "totals_mismatch",
        8: "due_before_issue",
        11: "invalid_tax_id",
    }
    for i in range(14):
        files.append(
            (
                f"invoice_{i + 1:02d}",
                [
                    invoice(
                        "tr" if i % 2 == 0 else "en",
                        8 if i in (3, 6, 9) else rng.randrange(2, 6),
                        faults.get(i),
                    )
                ],
            )
        )
    for i in range(8):
        files.append((f"delivery_note_{i + 1:02d}", [delivery_note("tr" if i % 2 == 0 else "en")]))
    for i in range(7):
        files.append(
            (
                f"policy_{i + 1:02d}",
                [policy("tr" if i % 2 == 0 else "en", "invalid_period" if i == 4 else None)],
            )
        )
    for i, text in enumerate(OTHER):
        files.append(
            (
                f"other_{i + 1:02d}",
                [(text, {"type": "unknown", "fields": {}, "expected_errors": []})],
            )
        )
    bundles = [
        [delivery_note("tr"), invoice("tr", 3)],
        [invoice("en", 8), delivery_note("en")],
        [policy("tr"), invoice("tr", 4), delivery_note("tr")],
        [invoice("en", 2), invoice("en", 3, "totals_mismatch")],
        [delivery_note("tr"), delivery_note("tr"), invoice("tr", 8)],
    ]
    for i, parts in enumerate(bundles):
        files.append((f"bundle_{i + 1:02d}", parts))
    for name, parts in files:
        (docs / f"{name}.txt").write_text("\f".join(t for t, _ in parts) + "\n", encoding="utf-8")
        (gold / f"{name}.json").write_text(
            json.dumps(
                {"file": f"{name}.txt", "documents": [g for _, g in parts]},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(f"wrote {len(files)} files, {sum(len(p) for _, p in files)} documents")


if __name__ == "__main__":
    main()
