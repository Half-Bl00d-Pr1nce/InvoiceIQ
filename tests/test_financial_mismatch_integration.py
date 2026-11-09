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
    test_db = tmp_path / "invoiceiq_financial_mismatch_test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)

    initialize_database()
    migrate_database()
    load_reference_data()

    yield test_db


def make_financially_inconsistent_invoice():
    return InvoiceData(
        vendor=VendorDetails(
            vendor_name="Chennai Industrial Supplies",
            vendor_id="V001",
            tax_id="33ABCDE1234F1Z5",
        ),
        invoice_number="CIS-FIN-ERROR-001",
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
        # Incorrect: expected total is ₹5,900, not ₹6,000.
        total_amount=Decimal("6000.00"),
        tax_treatment="EXCLUSIVE",
    )


def test_financial_mismatch_routes_invoice_to_review(
    isolated_database, monkeypatch
):
    pdf_path = SAMPLE_INVOICES / "InvoiceIQ_Valid_Test_Invoice.pdf"
    assert pdf_path.is_file(), f"Sample PDF not found: {pdf_path}"

    invoice_data = make_financially_inconsistent_invoice()

    monkeypatch.setattr(
        pipeline,
        "extract_invoice_data",
        lambda extracted_text: invoice_data,
    )

    result = pipeline.process_invoice(pdf_path)

    assert result["vendor_validation"]["status"] == "PASS"
    assert result["po_validation"]["status"] == "PASS"
    assert result["po_validation"]["po_id"] == "PO-1001"
    assert result["duplicate_validation"]["status"] == "PASS"

    # The subtotal is correct, but the declared invoice total is not.
    assert result["financial_validation"]["subtotal"]["status"] == "PASS"
    assert result["financial_validation"]["total"]["status"] == "FAIL"

    # A financial discrepancy must not be automatically approved.
    assert result["decision"]["status"] == "PENDING_REVIEW"
    assert result["invoice_id"] is not None

    connection = sqlite3.connect(isolated_database)
    connection.row_factory = sqlite3.Row

    try:
        saved_invoice = connection.execute(
            "SELECT * FROM invoices WHERE invoice_id = ?",
            (result["invoice_id"],),
        ).fetchone()
    finally:
        connection.close()

    assert saved_invoice is not None
    assert saved_invoice["status"] == "PENDING_REVIEW"