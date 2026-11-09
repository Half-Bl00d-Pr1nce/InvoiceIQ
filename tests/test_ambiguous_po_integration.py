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
    test_db = tmp_path / "invoiceiq_ambiguous_po_test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)

    initialize_database()
    migrate_database()
    load_reference_data()

    yield test_db


def make_ambiguous_invoice():
    return InvoiceData(
        vendor=VendorDetails(
            vendor_name="Metro Electrical Traders",
            vendor_id="V002",
            tax_id="33BCDEF2345G1Z6",
        ),
        invoice_number="MET-INV-2026-051",
        invoice_date="2026-11-07",
        po_number=None,
        currency="INR",
        items=[
            InvoiceItem(
                item_code=None,
                description="Electrical Copper Cable 2.5mm",
                quantity=Decimal("10"),
                unit_price=Decimal("1200.00"),
                line_amount=Decimal("12000.00"),
                tax_rate=Decimal("18"),
            )
        ],
        subtotal=Decimal("12000.00"),
        shipping=Decimal("0"),
        discount=Decimal("0"),
        tax_amount=Decimal("2160.00"),
        total_amount=Decimal("14160.00"),
        tax_treatment="EXCLUSIVE",
    )


def test_missing_po_with_ambiguous_candidates_goes_to_review(
    isolated_database, monkeypatch
):
    pdf_path = (
        SAMPLE_INVOICES
        / "InvoiceIQ_missing_PO_ambiguous_match_fresh_051.pdf"
    )

    assert pdf_path.is_file(), f"Sample PDF not found: {pdf_path}"

    invoice_data = make_ambiguous_invoice()

    monkeypatch.setattr(
        pipeline,
        "extract_invoice_data",
        lambda extracted_text: invoice_data,
    )

    result = pipeline.process_invoice(pdf_path)

    # Document and vendor validation
    assert result["document"]["document_type"] == "DIGITAL"
    assert result["vendor_validation"]["status"] == "PASS"

    # No explicit PO and multiple plausible candidates
    assert result["po_validation"]["status"] == "REVIEW"
    assert result["po_validation"].get("po_id") is None

    # Financial checks should still succeed
    assert result["financial_validation"]["subtotal"]["status"] == "PASS"
    assert result["financial_validation"]["total"]["status"] == "PASS"

    # Without a confirmed PO, item reconciliation must not run
    assert result["item_reconciliation"]["status"] == "NOT_CHECKED"

    # A fresh isolated database should not flag this as a duplicate
    assert result["duplicate_validation"]["status"] == "PASS"

    # Ambiguous PO identification requires human review
    assert result["decision"]["status"] == "PENDING_REVIEW"

    # Verify persistence
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