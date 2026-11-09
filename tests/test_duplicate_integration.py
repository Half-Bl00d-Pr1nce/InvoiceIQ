from decimal import Decimal
from pathlib import Path
import sqlite3

import pytest

import src.database.db as db
import src.pipeline as pipeline
from src.database.db import initialize_database, migrate_database
from src.database.repository import load_reference_data
from src.extraction.schemas import InvoiceData, InvoiceItem, VendorDetails


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INVOICES = PROJECT_ROOT / "sample_invoices"


@pytest.fixture
def isolated_database(tmp_path, monkeypatch):
    test_db = tmp_path / "invoiceiq_duplicate_test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)

    initialize_database()
    migrate_database()
    load_reference_data()

    yield test_db


def make_invoice():
    return InvoiceData(
        vendor=VendorDetails(
            vendor_name="Chennai Industrial Supplies",
            vendor_id="V001",
            tax_id="33ABCDE1234F1Z5",
        ),
        invoice_number="CIS-INV-DUP-001",
        invoice_date="2026-11-08",
        po_number="PO-1001",
        currency="INR",
        items=[
            InvoiceItem(
                item_code="BOLT-M10",
                description="Industrial Steel Bolt M10",
                quantity=Decimal("10"),
                unit_price=Decimal("500.00"),
                line_amount=Decimal("5000.00"),
                tax_rate=Decimal("18"),
            )
        ],
        subtotal=Decimal("5000.00"),
        shipping=Decimal("0"),
        discount=Decimal("0"),
        tax_amount=Decimal("900.00"),
        total_amount=Decimal("5900.00"),
        tax_treatment="EXCLUSIVE",
    )


def test_same_pdf_submitted_twice_is_rejected(
    isolated_database, monkeypatch
):
    pdf_path = SAMPLE_INVOICES / "InvoiceIQ_Valid_Test_Invoice.pdf"
    assert pdf_path.is_file(), f"Sample PDF not found: {pdf_path}"

    invoice_data = make_invoice()

    monkeypatch.setattr(
        pipeline,
        "extract_invoice_data",
        lambda extracted_text: invoice_data,
    )

    # First submission
    first_result = pipeline.process_invoice(pdf_path)

    assert first_result["duplicate_validation"]["status"] == "PASS"
    assert first_result["decision"]["status"] == "APPROVED"
    assert first_result["invoice_id"] is not None

    # Second submission: exactly the same PDF
    second_result = pipeline.process_invoice(pdf_path)

    assert second_result["duplicate_validation"]["status"] == "FAIL"
    assert second_result["decision"]["status"] == "REJECTED"

    # A duplicate must not create another invoice record.
    assert second_result["invoice_id"] is None

    connection = sqlite3.connect(isolated_database)

    try:
        invoice_count = connection.execute(
            "SELECT COUNT(*) FROM invoices"
        ).fetchone()[0]
    finally:
        connection.close()

    assert invoice_count == 1