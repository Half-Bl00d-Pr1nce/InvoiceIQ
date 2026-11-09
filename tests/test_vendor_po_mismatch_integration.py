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
    test_db = tmp_path / "invoiceiq_vendor_po_mismatch_test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)

    initialize_database()
    migrate_database()
    load_reference_data()

    yield test_db


def test_vendor_cannot_use_another_vendors_po(
    isolated_database, monkeypatch
):
    source_pdf = SAMPLE_INVOICES / "InvoiceIQ_Valid_Test_Invoice.pdf"
    assert source_pdf.is_file(), f"Sample PDF not found: {source_pdf}"

    # Vendor V001 is valid, but PO-1002 belongs to Vendor V002.
    invoice_data = InvoiceData(
        vendor=VendorDetails(
            vendor_name="Chennai Industrial Supplies",
            vendor_id="V001",
            tax_id="33ABCDE1234F1Z5",
        ),
        invoice_number="CIS-PO-MISMATCH-001",
        invoice_date="2026-11-08",
        po_number="PO-1002",
        currency="INR",
        items=[
            InvoiceItem(
                item_code="CABLE-2.5",
                description="Electrical Copper Cable 2.5mm",
                quantity=Decimal("1"),
                unit_price=Decimal("1200.00"),
                line_amount=Decimal("1200.00"),
                tax_rate=Decimal("18"),
            )
        ],
        subtotal=Decimal("1200.00"),
        shipping=Decimal("0"),
        discount=Decimal("0"),
        tax_amount=Decimal("216.00"),
        total_amount=Decimal("1416.00"),
        tax_treatment="EXCLUSIVE",
    )

    monkeypatch.setattr(
        pipeline,
        "extract_invoice_data",
        lambda extracted_text: invoice_data,
    )

    result = pipeline.process_invoice(source_pdf)

    # Vendor itself is approved.
    assert result["vendor_validation"]["status"] == "PASS"

    # The PO belongs to a different vendor.
    assert result["po_validation"]["status"] == "FAIL"

    # A vendor/PO ownership mismatch must cause rejection.
    assert result["decision"]["status"] == "REJECTED"

    # Confirm that the rejected invoice is persisted.
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