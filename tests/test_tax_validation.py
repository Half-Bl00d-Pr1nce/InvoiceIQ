
from decimal import Decimal

from src.extraction.schemas import InvoiceData, InvoiceItem
from src.validation.financial_checks import validate_invoice_total


def create_invoice(tax_treatment, subtotal, tax, total):
    return InvoiceData(
        currency="INR",
        items=[
            InvoiceItem(
                item_code="ITEM-001",
                description="Industrial component",
                quantity=Decimal("1"),
                unit_price=Decimal("10000"),
                line_amount=Decimal("10000"),
                tax_rate=Decimal("18")
            )
        ],
        subtotal=Decimal(subtotal),
        shipping=Decimal("0"),
        discount=Decimal("0"),
        tax_amount=Decimal(tax),
        total_amount=Decimal(total),
        tax_treatment=tax_treatment
    )


def test_exclusive_tax_total():
    invoice = create_invoice(
        "EXCLUSIVE", "10000", "1800", "11800"
    )

    result = validate_invoice_total(invoice)

    assert result["status"] == "PASS"


def test_inclusive_tax_total():
    invoice = create_invoice(
        "INCLUSIVE", "11800", "1800", "11800"
    )

    result = validate_invoice_total(invoice)

    assert result["status"] == "PASS"


def test_unknown_tax_treatment_requires_review():
    invoice = create_invoice(
        "UNKNOWN", "10000", "1800", "11800"
    )

    result = validate_invoice_total(invoice)

    assert result["status"] == "NOT_CHECKED"
