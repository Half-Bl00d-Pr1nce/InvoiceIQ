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
    """Give every integration test a clean DB without touching the real DB."""
    test_db = tmp_path / "invoiceiq_integration_test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)

    initialize_database()
    migrate_database()
    load_reference_data()

    yield test_db


def make_valid_invoice():
    """Structured extraction expected from the valid PO-1001 sample PDF."""
    return InvoiceData(
        vendor=VendorDetails(
            vendor_name="Chennai Industrial Supplies",
            vendor_id="V001",
            tax_id="33ABCDE1234F1Z5",
        ),
        invoice_number="CIS-INV-2026-001",
        invoice_date="2026-11-05",
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


def make_bundled_invoice():
    """Structured extraction expected from the bundled PO-1004 sample PDF."""
    return InvoiceData(
        vendor=VendorDetails(
            vendor_name="Chennai Industrial Supplies",
            vendor_id="V001",
            tax_id="33ABCDE1234F1Z5",
        ),
        invoice_number="INV-BUNDLE-001",
        invoice_date="2026-11-08",
        po_number="PO-1004",
        currency="INR",
        items=[
            InvoiceItem(
                item_code=None,
                description="Bolt, Nut and Washer Kit",
                quantity=Decimal("1"),
                unit_price=Decimal("800.00"),
                line_amount=Decimal("800.00"),
                tax_rate=Decimal("9"),
            )
        ],
        subtotal=Decimal("800.00"),
        shipping=Decimal("0"),
        discount=Decimal("0"),
        tax_amount=Decimal("144.00"),
        total_amount=Decimal("944.00"),
        tax_treatment="EXCLUSIVE",
    )


def run_with_mocked_extraction(monkeypatch, pdf_name, invoice_data):
    """Keep PDF ingestion real; replace only the local LLM extraction call."""
    pdf_path = SAMPLE_INVOICES / pdf_name
    assert pdf_path.is_file(), (
        f"Sample PDF not found: {pdf_path}. "
        "Keep the sample_invoices folder in the project root."
    )

    monkeypatch.setattr(
        pipeline,
        "extract_invoice_data",
        lambda extracted_text: invoice_data,
    )

    return pipeline.process_invoice(pdf_path)


def read_invoice_row(database_path, invoice_id):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute(
            "SELECT * FROM invoices WHERE invoice_id = ?",
            (invoice_id,),
        ).fetchone()
    finally:
        connection.close()


def test_valid_invoice_runs_through_pipeline_and_persists(
    isolated_database, monkeypatch
):
    result = run_with_mocked_extraction(
        monkeypatch,
        "InvoiceIQ_Valid_Test_Invoice.pdf",
        make_valid_invoice(),
    )

    assert result["document"]["document_type"] == "DIGITAL"
    assert result["vendor_validation"]["status"] == "PASS"
    assert result["po_validation"]["status"] == "PASS"
    assert result["po_validation"]["po_id"] == "PO-1001"
    assert result["financial_validation"]["subtotal"]["status"] == "PASS"
    assert result["financial_validation"]["total"]["status"] == "PASS"
    assert result["item_reconciliation"]["status"] == "PASS"
    assert result["duplicate_validation"]["status"] == "PASS"
    assert result["decision"]["status"] == "APPROVED"

    # Verify that the final decision was actually written to SQLite.
    saved_invoice = read_invoice_row(isolated_database, result["invoice_id"])
    assert saved_invoice is not None
    assert saved_invoice["status"] == "APPROVED"
    assert saved_invoice["vendor_id"] == "V001"
    assert saved_invoice["po_id"] == "PO-1001"


def test_bundled_invoice_is_routed_to_review_without_component_allocation(
    isolated_database, monkeypatch
):
    result = run_with_mocked_extraction(
        monkeypatch,
        "InvoiceIQ_Bundled_Test_INV-BUNDLE-001.pdf",
        make_bundled_invoice(),
    )

    assert result["document"]["document_type"] == "DIGITAL"
    assert result["vendor_validation"]["status"] == "PASS"
    assert result["po_validation"]["status"] == "PASS"
    assert result["po_validation"]["po_id"] == "PO-1004"
    assert result["financial_validation"]["subtotal"]["status"] == "PASS"
    assert result["financial_validation"]["total"]["status"] == "PASS"
    assert result["duplicate_validation"]["status"] == "PASS"

    reconciliation = result["item_reconciliation"]
    assert reconciliation["status"] == "REVIEW"
    assert len(reconciliation["results"]) == 1

    bundle_result = reconciliation["results"][0]
    assert bundle_result["is_bundle"] is True
    assert len(bundle_result["suggested_components"]) >= 2

    # The system must suggest components, not invent quantities or prices.
    assert result["invoice_data"].items[0].item_code is None
    assert result["invoice_data"].items[0].quantity == Decimal("1")
    assert result["invoice_data"].items[0].unit_price == Decimal("800.00")
    assert result["decision"]["status"] == "PENDING_REVIEW"

    saved_invoice = read_invoice_row(isolated_database, result["invoice_id"])
    assert saved_invoice is not None
    assert saved_invoice["status"] == "PENDING_REVIEW"
    assert saved_invoice["po_id"] == "PO-1004"
