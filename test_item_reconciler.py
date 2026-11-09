import pandas as pd
from decimal import Decimal

from src.extraction.schemas import InvoiceItem
from src.matching.item_reconciler import reconcile_invoice_items


purchase_orders_df = pd.read_csv("data/purchase_orders.csv")


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


# Test 1: Exact match
print("\nEXACT MATCH:")
print(reconcile_invoice_items(
    [create_invoice_item()],
    "PO-1001",
    purchase_orders_df
))


# Test 2: Partial invoicing
print("\nPARTIAL INVOICING:")
print(reconcile_invoice_items(
    [create_invoice_item(quantity="90")],
    "PO-1001",
    purchase_orders_df
))


# Test 3: Excess quantity
print("\nEXCESS QUANTITY:")
print(reconcile_invoice_items(
    [create_invoice_item(quantity="110")],
    "PO-1001",
    purchase_orders_df
))


# Test 4: Price mismatch
print("\nPRICE MISMATCH:")
print(reconcile_invoice_items(
    [create_invoice_item(unit_price="550")],
    "PO-1001",
    purchase_orders_df
))


# Test 5: Unknown item code
print("\nUNKNOWN ITEM:")
print(reconcile_invoice_items(
    [create_invoice_item(item_code="UNKNOWN-001")],
    "PO-1001",
    purchase_orders_df
))