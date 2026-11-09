from decimal import Decimal
from copy import deepcopy

from src.extraction.schemas import InvoiceData, VendorDetails, InvoiceItem
from src.validation.financial_checks import validate_financials


# Reusable sample invoice
def create_sample_invoice():

    return InvoiceData(
        vendor=VendorDetails(
            vendor_name="BioHue Chemicals",
            vendor_address="77 Maple Ave, Boston, MA, USA"
        ),
        invoice_number="INV-30102",
        invoice_date="2026-01-13",
        due_date="2026-01-27",
        po_number=None,
        currency="USD",

        items=[
            InvoiceItem(
                item_code="PIG-777",
                description="Eco-Friendly Pigment Pack",
                quantity=Decimal("4"),
                unit_price=Decimal("75"),
                line_amount=Decimal("300"),
                tax_rate=Decimal("5.5")
            ),
            InvoiceItem(
                item_code="NAT-112",
                description="Natural Clay Filler",
                quantity=Decimal("4"),
                unit_price=Decimal("45"),
                line_amount=Decimal("180"),
                tax_rate=Decimal("5.5")
            )
        ],

        subtotal=Decimal("480"),
        shipping=Decimal("110"),
        discount=Decimal("0"),
        tax_amount=Decimal("26.40"),
        total_amount=Decimal("616.40"),
        tax_treatment="EXCLUSIVE"
    )


# Test 1: Correct invoice should pass all checks
def test_valid_invoice():

    invoice = create_sample_invoice()
    results = validate_financials(invoice)

    for item in results["line_items"]["results"]:
        assert item["status"] == "PASS"

    assert results["subtotal"]["status"] == "PASS"
    assert results["total"]["status"] == "PASS"


# Test 2: Incorrect line amount
def test_incorrect_line_amount():

    invoice = create_sample_invoice()
    invoice.items[0].line_amount = Decimal("320")

    results = validate_financials(invoice)

    assert results["line_items"]["results"][0]["status"] == "FAIL"
    assert results["subtotal"]["status"] == "FAIL"


# Test 3: Incorrect subtotal
def test_incorrect_subtotal():

    invoice = create_sample_invoice()
    invoice.subtotal = Decimal("500")

    results = validate_financials(invoice)

    assert results["subtotal"]["status"] == "FAIL"
    assert results["total"]["status"] == "FAIL"


# Test 4: Incorrect invoice total
def test_incorrect_invoice_total():

    invoice = create_sample_invoice()
    invoice.total_amount = Decimal("650")

    results = validate_financials(invoice)

    assert results["total"]["status"] == "FAIL"