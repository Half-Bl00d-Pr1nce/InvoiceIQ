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
    """Use one clean database for this test; never touch the main database."""
    test_db = tmp_path / "invoiceiq_split_integration_test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)

    initialize_database()
    migrate_database()
    load_reference_data()

    yield test_db


def make_split_invoice(invoice_number, quantity):
    unit_price = Decimal("1200.00")
    subtotal = unit_price * Decimal(quantity)
    tax_amount = subtotal * Decimal("0.18")
    total_amount = subtotal + tax_amount

    return InvoiceData(
        vendor=VendorDetails(
            vendor_name="Metro Electrical Traders",
            vendor_id="V002",
            tax_id="33BCDEF2345G1Z6",
        ),
        invoice_number=invoice_number,
        invoice_date="2026-11-08",
        po_number="PO-1002",
        currency="INR",
        items=[
            InvoiceItem(
                item_code="CABLE-2.5",
                description="Electrical Copper Cable 2.5mm",
                quantity=Decimal(quantity),
                unit_price=unit_price,
                line_amount=subtotal,
                tax_rate=Decimal("18"),
            )
        ],
        subtotal=subtotal,
        shipping=Decimal("0"),
        discount=Decimal("0"),
        tax_amount=tax_amount,
        total_amount=total_amount,
        tax_treatment="EXCLUSIVE",
    )


def run_with_mocked_extraction(monkeypatch, pdf_name, invoice_data):
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


def test_split_invoices_respect_cumulative_po_quantity(
    isolated_database, monkeypatch
):
    # PO-1002 permits 50 units. The first invoice bills 40 units.
    first_result = run_with_mocked_extraction(
        monkeypatch,
        "InvoiceIQ_Split_Invoice_1_40_units.pdf",
        make_split_invoice("MET-SPLIT-2026-001", 40),
    )

    assert first_result["vendor_validation"]["status"] == "PASS"
    assert first_result["po_validation"]["status"] == "PASS"
    assert first_result["po_validation"]["po_id"] == "PO-1002"
    assert first_result["item_reconciliation"]["status"] == "PASS"
    assert first_result["duplicate_validation"]["status"] == "PASS"
    assert first_result["decision"]["status"] == "APPROVED"

    first_saved = read_invoice_row(
        isolated_database, first_result["invoice_id"]
    )
    assert first_saved is not None
    assert first_saved["status"] == "APPROVED"

    # The second invoice bills 20 more units: cumulative billing is now 60.
    # It must see the first invoice in the same database and flag the 10-unit
    # excess against the PO quantity of 50.
    second_result = run_with_mocked_extraction(
        monkeypatch,
        "InvoiceIQ_Split_Invoice_2_20_units.pdf",
        make_split_invoice("MET-SPLIT-2026-002", 20),
    )

    assert second_result["vendor_validation"]["status"] == "PASS"
    assert second_result["po_validation"]["status"] == "PASS"
    assert second_result["po_validation"]["po_id"] == "PO-1002"
    assert second_result["duplicate_validation"]["status"] == "PASS"
    assert second_result["item_reconciliation"]["status"] in {"FAIL", "REVIEW"}
    assert second_result["decision"]["status"] == "PENDING_REVIEW"

    second_saved = read_invoice_row(
        isolated_database, second_result["invoice_id"]
    )
    assert second_saved is not None
    assert second_saved["status"] == "PENDING_REVIEW"

    # Both invoices must be persisted; the first must remain approved.
    first_saved_after_second = read_invoice_row(
        isolated_database, first_result["invoice_id"]
    )
    assert first_saved_after_second["status"] == "APPROVED"
