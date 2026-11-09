
import pytest

from src.database import db
from src.database import repository
from src.extraction.schemas import InvoiceData


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    # Redirect all database operations to a temporary database.
    test_database_path = tmp_path / "test_invoiceiq.db"

    monkeypatch.setattr(db, "DB_PATH", test_database_path)

    db.initialize_database()
    db.migrate_database()

    yield test_database_path


@pytest.fixture
def sample_invoice():
    return InvoiceData.model_validate({
        "vendor": {
            "vendor_name": "Persistence Test Vendor"
        },
        "invoice_number": "TEST-PERSIST-001",
        "invoice_date": "2026-11-05",
        "currency": "INR",
        "items": [
            {
                "item_code": "ITEM-001",
                "description": "Test Product",
                "quantity": "2",
                "unit_price": "50",
                "line_amount": "100"
            }
        ],
        "subtotal": "100",
        "shipping": "0",
        "tax_amount": "0",
        "total_amount": "100",
        "tax_treatment": "EXCLUSIVE"
    })


def test_invoice_persistence(test_db, sample_invoice):
    invoice_id = repository.create_invoice_record(
        invoice=sample_invoice,
        file_name="test_invoice.pdf",
        file_hash="test-persistence-hash-001"
    )

    repository.save_invoice_items(
        invoice_id,
        sample_invoice.items,
        sample_invoice.currency
    )

    repository.save_validation_results(
        invoice_id,
        {
            "vendor": {
                "status": "PASS",
                "message": "Vendor validation passed."
            },
            "financial": {
                "status": "PASS",
                "message": "Financial validation passed."
            }
        }
    )

    repository.save_processing_log(
        invoice_id,
        "EXTRACTION",
        "PASS",
        "Invoice extracted successfully."
    )

    repository.update_invoice_status(invoice_id, "APPROVED")

    connection = db.get_connection()

    try:
        invoice = connection.execute(
            "SELECT * FROM invoices WHERE invoice_id = ?",
            (invoice_id,)
        ).fetchone()

        items = connection.execute(
            "SELECT * FROM invoice_items WHERE invoice_id = ?",
            (invoice_id,)
        ).fetchall()

        validations = connection.execute(
            "SELECT * FROM validation_results WHERE invoice_id = ?",
            (invoice_id,)
        ).fetchall()

        logs = connection.execute(
            "SELECT * FROM processing_logs WHERE invoice_id = ?",
            (invoice_id,)
        ).fetchall()

        assert invoice is not None
        assert invoice["invoice_number"] == "TEST-PERSIST-001"
        assert invoice["status"] == "APPROVED"

        assert len(items) == 1
        assert items[0]["description"] == "Test Product"
        assert items[0]["line_total_paise"] == 10000

        assert len(validations) == 2
        assert len(logs) == 1
        assert logs[0]["stage"] == "EXTRACTION"

    finally:
        connection.close()


def test_invalid_invoice_status_is_rejected(test_db, sample_invoice):
    invoice_id = repository.create_invoice_record(
        invoice=sample_invoice,
        file_name="test_invoice.pdf",
        file_hash="test-invalid-status-hash"
    )

    with pytest.raises(ValueError, match="Invalid invoice status"):
        repository.update_invoice_status(invoice_id, "INVALID")


def test_nonexistent_invoice_status_update_is_rejected(test_db):
    with pytest.raises(ValueError, match="does not exist"):
        repository.update_invoice_status(99999, "APPROVED")
