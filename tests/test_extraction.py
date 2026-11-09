
from datetime import date
from decimal import Decimal

import pytest

from src.extraction.schemas import InvoiceData, InvoiceItem
from src.extraction.llm_extractor import (
    clean_extracted_items,
    extract_invoice_data,
)


def test_valid_invoice_schema():
    invoice = InvoiceData.model_validate({
        "vendor": {
            "vendor_name": "Chennai Industrial Supplies",
            "tax_id": "33ABCDE1234F1Z5"
        },
        "invoice_number": "INV-001",
        "invoice_date": "2026-11-08",
        "items": [
            {
                "item_code": "BOLT-M10",
                "description": "Industrial Steel Bolt",
                "quantity": "10",
                "unit_price": "500",
                "line_amount": "5000"
            }
        ],
        "subtotal": "5000",
        "tax_amount": "900",
        "total_amount": "5900",
        "tax_treatment": "EXCLUSIVE"
    })

    assert invoice.invoice_number == "INV-001"
    assert invoice.invoice_date == date(2026, 11, 8)
    assert invoice.items[0].quantity == Decimal("10")
    assert invoice.total_amount == Decimal("5900")


def test_missing_vendor_fields_are_normalised():
    invoice = InvoiceData.model_validate({
        "vendor": {
            "vendor_name": "N/A",
            "tax_id": "null"
        }
    })

    assert invoice.vendor.vendor_name is None
    assert invoice.vendor.tax_id is None


def test_optional_invoice_fields():
    invoice = InvoiceData.model_validate({})

    assert invoice.vendor is not None
    assert invoice.items == []
    assert invoice.tax_treatment == "UNKNOWN"
    assert invoice.invoice_number is None


def test_invalid_invoice_date_is_rejected():
    with pytest.raises(ValueError):
        InvoiceData.model_validate({
            "invoice_date": "not-a-date"
        })


def test_invalid_tax_treatment_is_rejected():
    with pytest.raises(ValueError):
        InvoiceData.model_validate({
            "tax_treatment": "PARTIAL"
        })


def test_summary_rows_are_removed():
    invoice = InvoiceData.model_validate({
        "items": [
            {
                "description": "Industrial Steel Bolt",
                "quantity": "10",
                "unit_price": "500",
                "line_amount": "5000"
            },
            {
                "description": "CGST 9%",
                "line_amount": "450"
            },
            {
                "description": "SGST 9%",
                "line_amount": "450"
            },
            {
                "description": "Grand Total",
                "line_amount": "5900"
            }
        ]
    })

    cleaned = clean_extracted_items(invoice)

    assert len(cleaned.items) == 1
    assert cleaned.items[0].description == "Industrial Steel Bolt"


def test_item_code_identical_to_description_becomes_none():
    invoice = InvoiceData.model_validate({
        "items": [
            {
                "item_code": "Industrial Steel Bolt",
                "description": "industrial steel bolt",
                "quantity": "10"
            }
        ]
    })

    cleaned = clean_extracted_items(invoice)

    assert cleaned.items[0].item_code is None


def test_genuine_bundle_line_is_preserved():
    invoice = InvoiceData.model_validate({
        "items": [
            {
                "description": "Bolt, Nut and Washer Kit",
                "quantity": "1",
                "unit_price": "800",
                "line_amount": "800"
            }
        ]
    })

    cleaned = clean_extracted_items(invoice)

    assert len(cleaned.items) == 1
    assert cleaned.items[0].description == "Bolt, Nut and Washer Kit"


def test_empty_invoice_text_is_rejected():
    with pytest.raises(ValueError, match="Invoice text is empty"):
        extract_invoice_data("")

    with pytest.raises(ValueError, match="Invoice text is empty"):
        extract_invoice_data("   ")
