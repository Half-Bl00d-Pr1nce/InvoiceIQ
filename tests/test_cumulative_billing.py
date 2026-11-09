
import pandas as pd
import pytest

from types import SimpleNamespace

from src.database import db
from src.database.db import initialize_database
from src.matching.item_reconciler import reconcile_invoice_items


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    # Give each test its own temporary SQLite database.
    monkeypatch.setattr(
        db,
        "DB_PATH",
        tmp_path / "test_invoiceiq.db"
    )

    initialize_database()

    connection = db.get_connection()

    
    # Create a test vendor.
    connection.execute(
        """
        INSERT INTO vendors
        (vendor_id, vendor_name, gstin, status, bank_ref)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "V-TEST-01",
            "Test Industrial Supplies",
            "TESTGSTIN",
            "ACTIVE",
            "TEST-BANK"
        )
    )

    # Create a PO with 100 bolts.
    connection.execute(
        """
        INSERT INTO purchase_orders
        (po_id, vendor_id, po_date, status, currency)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "PO-TEST-01",
            "V-TEST-01",
            "2026-10-01",
            "OPEN",
            "INR"
        )
    )


    connection.execute(
        """
        INSERT INTO po_items
        (
            po_item_id, po_id, item_code, description,
            quantity, unit_price_paise, tax_rate
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "PO-TEST-01-LINE-0001",
            "PO-TEST-01",
            "BOLT-M10",
            "Industrial Steel Bolt M10",
            100,
            50000,
            18
        )
    )

    connection.commit()

    yield connection

    connection.close()




def insert_historical_invoice(connection, quantity, status):
    invoice_number = f"TEST-{status}-{quantity}"
    file_name = f"{invoice_number}.pdf"
    file_hash = f"test-hash-{status}-{quantity}"

    cursor = connection.execute(
        """
        INSERT INTO invoices
        (
            invoice_number,
            po_id,
            status,
            file_name,
            file_hash,
            currency,
            total_amount_paise
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            invoice_number,
            "PO-TEST-01",
            status,
            file_name,
            file_hash,
            "INR",
            int(quantity * 50000)
        )
    )

    invoice_id = cursor.lastrowid

    connection.execute(
        """
        INSERT INTO invoice_items
        (
            invoice_id,
            item_code,
            description,
            quantity,
            unit_price_paise,
            tax_rate,
            line_total_paise
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            invoice_id,
            "BOLT-M10",
            "Industrial Steel Bolt M10",
            quantity,
            50000,
            18,
            int(quantity * 50000)
        )
    )

    connection.commit()




def create_po_dataframe():
    return pd.DataFrame([
        {
            "po_id": "PO-TEST-01",
            "item_code": "BOLT-M10",
            "description": "Industrial Steel Bolt M10",
            "quantity": 100,
            "unit_price_paise": 50000,
            "tax_rate": 18
        }
    ])


def create_invoice_item(quantity):
    return SimpleNamespace(
        item_code="BOLT-M10",
        quantity=quantity,
        unit_price=500,
        line_amount=quantity * 500
    )


def test_cumulative_quantity_within_limit(test_database):
    insert_historical_invoice(
        test_database,
        60,
        "APPROVED"
    )

    result = reconcile_invoice_items(
        [create_invoice_item(30)],
        "PO-TEST-01",
        create_po_dataframe()
    )

    assert result["status"] == "PASS"


def test_cumulative_quantity_exceeds_limit(test_database):
    insert_historical_invoice(
        test_database,
        60,
        "APPROVED"
    )

    result = reconcile_invoice_items(
        [create_invoice_item(50)],
        "PO-TEST-01",
        create_po_dataframe()
    )

    assert result["status"] == "FAIL"


def test_pending_invoice_creates_review(test_database):
    insert_historical_invoice(
        test_database,
        60,
        "APPROVED"
    )

    insert_historical_invoice(
        test_database,
        20,
        "PENDING_REVIEW"
    )

    result = reconcile_invoice_items(
        [create_invoice_item(30)],
        "PO-TEST-01",
        create_po_dataframe()
    )

    assert result["status"] == "REVIEW"
