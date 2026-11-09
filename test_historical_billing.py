
from src.database.repository import get_historical_po_billing

billing = get_historical_po_billing("PO-1001")

print("Historical billing for PO-1001:")
print(billing)

if not billing:
    print("\nNo historical invoices found. This is expected if you haven't processed any invoices yet.")
