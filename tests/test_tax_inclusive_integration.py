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
    """Use a clean temporary DB and preserve the user's working database."""
    test_db = tmp_path / "invoiceiq_tax_inclusive_test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)

    initialize_database()
    migrate_database()
    load_reference_data()

    yield test_db


def make_tax_inclusive_invoice():
    # ₹590 is the GST-inclusive price: ₹500 taxable value + ₹90 GST.
    return InvoiceData(
        vendor=VendorDetails(
            vendor_name="Chennai Industrial Supplies",
            vendor_id="V001",
            tax_id="33ABCDE1234F1Z5",
        ),
        invoice_number="CIS-TEST-2026-012",
        invoice_date="2026-11-08",
        po_number="PO-1001",
        currency="INR",
        items=[
            InvoiceItem(
                item_code="BOLT-M10",
                description="Industrial Steel Bolt M10",
                quantity=Decimal("1"),
                unit_price=Decimal("590.00"),
                line_amount=Decimal("590.00"),
                tax_rate=Decimal("18"),
            )
        ],
        subtotal=Decimal("590.00"),
        shipping=Decimal("0"),
        discount=Decimal("0"),
        tax_amount=Decimal("90.00"),
        total_amount=Decimal("590.00"),
        tax_treatment="INCLUSIVE",
    )


def test_tax_inclusive_invoice_is_normalised_and_reconciled(
    isolated_database, monkeypatch
):
    pdf_path = (
        SAMPLE_INVOICES / "Tax Inclusive Test Invoice CIS-TEST-2026-012.pdf"
    )
    assert pdf_path.is_file(), (
        f"Sample PDF not found: {pdf_path}. "
        "Keep the sample_invoices folder in the project root."
    )

    invoice_data = make_tax_inclusive_invoice()
    monkeypatch.setattr(
        pipeline,
        "extract_invoice_data",
        lambda extracted_text: invoice_data,
    )

    result = pipeline.process_invoice(pdf_path)

    assert result["document"]["document_type"] == "DIGITAL"
    assert result["vendor_validation"]["status"] == "PASS"
    assert result["po_validation"]["status"] == "PASS"
    assert result["po_validation"]["po_id"] == "PO-1001"
    assert result["financial_validation"]["subtotal"]["status"] == "PASS"
    assert result["financial_validation"]["total"]["status"] == "PASS"
    assert result["item_reconciliation"]["status"] == "PASS"
    assert result["duplicate_validation"]["status"] == "PASS"
    assert result["decision"]["status"] == "APPROVED"

    # The inclusive ₹590 line price must reconcile to the PO's ₹500
    # pre-tax unit price after removing 18% GST.
    reconciled_item = result["item_reconciliation"]["results"][0]
    assert reconciled_item["status"] == "PASS"

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
    assert saved_invoice["status"] == "APPROVED"
    assert saved_invoice["po_id"] == "PO-1001"