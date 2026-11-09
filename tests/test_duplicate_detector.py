import pytest

from src.database.db import initialize_database, get_connection
from src.validation.duplicate_detector import detect_duplicate
import src.database.db as db


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    database_path = tmp_path / "test_invoiceiq.db"
    monkeypatch.setattr(db, "DB_PATH", database_path)

    initialize_database()

    connection = get_connection()

    connection.execute(
        """
        INSERT INTO vendors
        (vendor_id, vendor_name, status)
        VALUES ('V001', 'Test Vendor', 'ACTIVE')
        """
    )

    connection.execute(
        """
        INSERT INTO invoices
        (
            vendor_id, invoice_number, invoice_date,
            total_amount_paise, file_name, file_hash, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "V001",
            "INV-001",
            "2026-10-01",
            100000,
            "invoice1.pdf",
            "hash-001",
            "APPROVED",
        ),
    )

    connection.commit()
    connection.close()

    return database_path


def test_same_file_hash_is_duplicate(test_database):
    result = detect_duplicate(file_hash="hash-001")

    assert result["status"] == "FAIL"
    assert result["match_type"] == "FILE_HASH"


def test_same_vendor_invoice_number_is_duplicate(test_database):
    result = detect_duplicate(
        vendor_id="V001",
        invoice_number="INV-001",
    )

    assert result["status"] == "FAIL"
    assert result["match_type"] == "VENDOR_INVOICE_NUMBER"


def test_same_vendor_date_amount_requires_review(test_database):
    result = detect_duplicate(
        vendor_id="V001",
        invoice_number="INV-002",
        invoice_date="2026-10-01",
        total_amount_paise=100000,
    )

    assert result["status"] == "REVIEW"
    assert result["match_type"] == "VENDOR_DATE_AMOUNT"


def test_new_invoice_passes(test_database):
    result = detect_duplicate(
        file_hash="new-hash",
        vendor_id="V001",
        invoice_number="INV-002",
        invoice_date="2026-10-02",
        total_amount_paise=200000,
    )

    assert result["status"] == "PASS"