
import pandas as pd
from types import SimpleNamespace

from src.matching.po_matcher import find_implicit_po_candidates


purchase_orders_df = pd.read_csv("data/purchase_orders.csv")

invoice_items = [
    SimpleNamespace(
        description="Electrical Copper Cable"
    )
]

result = find_implicit_po_candidates(
    vendor_id="V002",
    invoice_items=invoice_items,
    purchase_orders_df=purchase_orders_df
)

print("\nIMPLICIT PO MATCHING RESULT")
print(result)

print("\nCANDIDATES")
for candidate in result["candidates"]:
    print(candidate)
