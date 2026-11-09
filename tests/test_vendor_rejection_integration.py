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
    test_db = tmp_path / "invoiceiq_vendor_rejection_test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)

    initialize_database()
    migrate_database()
    load_reference_data()

    yield test_db


def make_unknown_vendor_invoice():
    return InvoiceData(
        vendor=VendorDetails(
            vendor_name="Unknown Industrial Traders",
            vendor_id="V999",
            tax_id=None,
        ),
        invoice_number="UNKNOWN-INV-001",
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


def test_unknown_vendor_is_rejected_by_full_pipeline(
    isolated_database, monkeypatch
):
    pdf_path = SAMPLE_INVOICES / "InvoiceIQ_Valid_Test_Invoice.pdf"
    assert pdf_path.is_file(), f"Sample PDF not found: {pdf_path}"

    invoice_data = make_unknown_vendor_invoice()

    monkeypatch.setattr(
        pipeline,
        "extract_invoice_data",
        lambda extracted_text: invoice_data,
    )

    result = pipeline.process_invoice(pdf_path)

    # Unknown vendor must fail vendor validation.
    assert result["vendor_validation"]["status"] == "FAIL"

    # A PO reference must not override failed vendor validation.
    assert result["po_validation"]["status"] == "NOT_CHECKED"

    # The final decision must be rejection.
    assert result["decision"]["status"] == "REJECTED"

    # Verify the rejected invoice was persisted for audit.
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
    assert saved_invoice["status"] == "REJECTED"