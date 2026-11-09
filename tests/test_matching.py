import pandas as pd
from decimal import Decimal
import pytest
import src.database.db as db_module
from src.extraction.schemas import InvoiceItem
from src.matching.item_reconciler import reconcile_invoice_items

@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):

    test_db_path = tmp_path / "test_invoiceiq.db"

    monkeypatch.setattr(
        db_module,
        "DB_PATH",
        test_db_path
    )

    db_module.initialize_database()
    
def create_po_data():
    return pd.DataFrame([
        {
            "po_id": "PO-1001",
            "vendor_id": "V001",
            "po_date": "2026-10-01",
            "status": "OPEN",
            "currency": "INR",
            "item_code": "BOLT-M10",
            "description": "Industrial Steel Bolt M10",
            "quantity": 100,
            "unit_price_paise": 50000,
            "tax_rate": 18
        }
    ])


def create_invoice_item(
    item_code="BOLT-M10",
    quantity="100",
    unit_price="500"
):
    return InvoiceItem(
        item_code=item_code,
        description="Industrial Steel Bolt M10",
        quantity=Decimal(quantity),
        unit_price=Decimal(unit_price),
        line_amount=Decimal(quantity) * Decimal(unit_price)
    )


def test_exact_item_match():
    result = reconcile_invoice_items(
        [create_invoice_item()],
        "PO-1001",
        create_po_data()
    )

    assert result["status"] == "PASS"



def test_partial_quantity():
    result = reconcile_invoice_items(
        [create_invoice_item(quantity="90")],
        "PO-1001",
        create_po_data()
    )

    assert result["status"] == "PASS"



def test_excess_quantity():
    result = reconcile_invoice_items(
        [create_invoice_item(quantity="110")],
        "PO-1001",
        create_po_data()
    )

    assert result["status"] == "FAIL"


def test_price_mismatch():
    result = reconcile_invoice_items(
        [create_invoice_item(unit_price="550")],
        "PO-1001",
        create_po_data()
    )

    assert result["status"] == "FAIL"


def test_unknown_item():
    result = reconcile_invoice_items(
        [create_invoice_item(item_code="UNKNOWN-001")],
        "PO-1001",
        create_po_data()
    )

    assert result["status"] == "FAIL"


def test_missing_po_items():
    result = reconcile_invoice_items(
        [create_invoice_item()],
        "PO-9999",
        create_po_data()
    )

    assert result["status"] == "FAIL"


def test_missing_item_code_returns_suggestions():
    item = create_invoice_item(quantity="10")
    item.description = "Industrial Steel Bolt M10"
    item.item_code = None

    result = reconcile_invoice_items(
        [item],
        "PO-1001",
        create_po_data()
    )

    assert result["status"] == "REVIEW"
    assert len(result["results"]) == 1

    matches = result["results"][0]["suggested_matches"]

    assert len(matches) > 0
    assert matches[0]["item_code"] == "BOLT-M10"


def test_bundled_description_requires_review():
    item = create_invoice_item(quantity="10")
    item.description = (
        "Industrial maintenance kit containing "
        "steel bolts and electrical cables"
    )
    item.item_code = None

    result = reconcile_invoice_items(
        [item],
        "PO-1001",
        create_po_data()
    )

    assert result["status"] == "REVIEW"
    assert result["results"][0]["status"] == "REVIEW"


def test_explicit_bundle_returns_component_suggestions():

    po_data = pd.DataFrame([
        {
            "po_id": "PO-2001",
            "vendor_id": "V001",
            "item_code": "BOLT-M10",
            "description": "Steel Bolt M10",
            "quantity": 10,
            "unit_price_paise": 5000,
            "tax_rate": 18
        },
        {
            "po_id": "PO-2001",
            "vendor_id": "V001",
            "item_code": "NUT-M10",
            "description": "Steel Nut M10",
            "quantity": 10,
            "unit_price_paise": 2000,
            "tax_rate": 18
        },
        {
            "po_id": "PO-2001",
            "vendor_id": "V001",
            "item_code": "WASHER-M10",
            "description": "Steel Washer M10",
            "quantity": 10,
            "unit_price_paise": 1000,
            "tax_rate": 18
        }
    ])

    item = create_invoice_item(
        item_code=None,
        quantity="10",
        unit_price="80"
    )

    item.description = "Bolt, Nut and Washer Kit"

    result = reconcile_invoice_items(
        [item],
        "PO-2001",
        po_data
    )

    assert result["status"] == "REVIEW"

    bundle_result = result["results"][0]

    assert bundle_result["is_bundle"] is True

    suggested_codes = {
        candidate["item_code"]
        for candidate in bundle_result["suggested_components"]
    }

    assert suggested_codes == {
        "BOLT-M10",
        "NUT-M10",
        "WASHER-M10"
    }

