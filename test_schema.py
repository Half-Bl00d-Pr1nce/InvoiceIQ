
from src.extraction.schemas import InvoiceData, InvoiceItem, FieldEvidence

invoice = InvoiceData(
    vendor={
        "vendor_name": "BioHue Chemicals",
        "vendor_address": "77 Maple Ave, Boston, MA, USA"
    },
    invoice_number="INV-30102",
    invoice_date="2026-01-13",
    due_date="2026-01-27",
    currency="USD",
    items=[
        InvoiceItem(
            item_code="PIG-777",
            description="Eco-Friendly Pigment Pack",
            quantity="4",
            unit_price="75.00",
            line_amount="300.00"
        ),
        InvoiceItem(
            item_code="NAT-112",
            description="Natural Clay Filler (40lb)",
            quantity="4",
            unit_price="45.00",
            line_amount="180.00"
        )
    ],
    subtotal="480.00",
    shipping="110.00",
    tax_amount="26.40",
    total_amount="616.40",
    tax_treatment="EXCLUSIVE",
    evidence={
        "invoice_number": FieldEvidence(
            page_number=1,
            supporting_text="Invoice Number: INV-30102"
        )
    }
)

print(invoice)
print("\nJSON OUTPUT:")
print(invoice.model_dump_json(indent=4))
