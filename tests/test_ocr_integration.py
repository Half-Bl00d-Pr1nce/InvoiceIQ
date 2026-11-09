from decimal import Decimal
from pathlib import Path
import sqlite3

import pymupdf
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
    test_db = tmp_path / "invoiceiq_ocr_integration_test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)

    initialize_database()
    migrate_database()
    load_reference_data()

    yield test_db


def create_scanned_copy(source_pdf, output_pdf):
    """Rasterise every source page into an image-only PDF."""
    source = pymupdf.open(source_pdf)
    scanned = pymupdf.open()

    try:
        for source_page in source:
            pixmap = source_page.get_pixmap(
                matrix=pymupdf.Matrix(2, 2),
                alpha=False,
            )

            scanned_page = scanned.new_page(
                width=source_page.rect.width,
                height=source_page.rect.height,
            )

            scanned_page.insert_image(
                scanned_page.rect,
                pixmap=pixmap,
            )

        scanned.save(output_pdf)
    finally:
        scanned.close()
        source.close()


def make_valid_invoice():
    return InvoiceData(
        vendor=VendorDetails(
            vendor_name="Chennai Industrial Supplies",
            vendor_id="V001",
            tax_id="33ABCDE1234F1Z5",
        ),
        invoice_number="CIS-OCR-TEST-001",
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


def test_scanned_pdf_uses_real_ocr_and_continues_through_pipeline(
    isolated_database, tmp_path, monkeypatch
):
    source_pdf = SAMPLE_INVOICES / "InvoiceIQ_Valid_Test_Invoice.pdf"
    assert source_pdf.is_file(), f"Sample PDF not found: {source_pdf}"

    scanned_pdf = tmp_path / "generated_scanned_invoice.pdf"
    create_scanned_copy(source_pdf, scanned_pdf)

    # Mock only LLM extraction. PDF rendering, Tesseract OCR,
    # document routing, matching, validation and persistence stay real.
    invoice_data = make_valid_invoice()
    monkeypatch.setattr(
        pipeline,
        "extract_invoice_data",
        lambda extracted_text: invoice_data,
    )

    result = pipeline.process_invoice(scanned_pdf)

    # Confirm that the document router actually selected OCR.
    assert result["document"]["document_type"] == "SCANNED"
    assert result["document"]["page_count"] >= 1
    assert all(
        page["source"] == "OCR"
        for page in result["document"]["pages"]
    )

    # OCR must have returned usable text.
    assert result["document"]["full_text"].strip()
    assert result["document"]["total_characters"] > 0

    # Confirm that the invoice continued through the real pipeline.
    assert result["vendor_validation"]["status"] == "PASS"
    assert result["po_validation"]["status"] == "PASS"
    assert result["po_validation"]["po_id"] == "PO-1001"
    assert result["financial_validation"]["subtotal"]["status"] == "PASS"
    assert result["financial_validation"]["total"]["status"] == "PASS"
    assert result["item_reconciliation"]["status"] == "PASS"
    assert result["duplicate_validation"]["status"] == "PASS"
    assert result["decision"]["status"] == "APPROVED"

    # Verify final status persistence.
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