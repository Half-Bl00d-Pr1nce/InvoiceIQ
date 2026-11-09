
from src.extraction.schemas import InvoiceData, InvoiceItem
from src.validation.financial_checks import validate_financials
from decimal import Decimal
from copy import deepcopy


invoice = InvoiceData(
    vendor={
        "vendor_name": "BioHue Chemicals"
    },
    invoice_number="INV-30102",
    currency="USD",
    items=[
        InvoiceItem(
            item_code="PIG-777",
            description="Eco-Friendly Pigment Pack",
            quantity="4",
            unit_price="75",
            line_amount="300"
        ),
        InvoiceItem(
            item_code="NAT-112",
            description="Natural Clay Filler (40lb)",
            quantity="4",
            unit_price="45",
            line_amount="180"
        )
    ],
    subtotal="480",
    shipping="110",
    tax_amount="26.40",
    total_amount="616.40",
    tax_treatment="EXCLUSIVE"
)


results = validate_financials(invoice)

print("\n========== FINANCIAL VALIDATION ==========")

for check_name, check_result in results.items():

    print(f"\n{check_name.upper()}")

    if check_name == "line_items":
        for item in check_result["results"]:
            print(item)
    else:
        print(check_result)


from copy import deepcopy


def run_test(test_name, modified_invoice):

    print(f"\n========== {test_name} ==========")

    results = validate_financials(modified_invoice)

    for check_name, check_result in results.items():

        print(f"\n{check_name.upper()}")

        if check_name == "line_items":
            for item in check_result["results"]:
                print(item)
        else:
            print(check_result)


# Test 1: Incorrect line amount
test_invoice_1 = deepcopy(invoice)
test_invoice_1.items[0].line_amount = Decimal("320")
run_test("INCORRECT LINE AMOUNT", test_invoice_1)

# Test 2: Incorrect subtotal
test_invoice_2 = deepcopy(invoice)
test_invoice_2.subtotal = Decimal("500")
run_test("INCORRECT SUBTOTAL", test_invoice_2)

# Test 3: Incorrect invoice total
test_invoice_3 = deepcopy(invoice)
test_invoice_3.total_amount = Decimal("650")
run_test("INCORRECT INVOICE TOTAL", test_invoice_3)
