import pandas as pd
from src.validation.vendor_checks import validate_vendor

vendors_df = pd.read_csv("data/vendors.csv")

# Correct Vendor ID + GSTIN, but incorrect extracted name
result = validate_vendor(
    vendor_name="InvoiceIQ Demo Company",
    vendor_id="V002",
    tax_id="33BCDEF2345G1Z6",
    vendors_df=vendors_df
)

print(result)

assert result["status"] == "PASS"
assert result["vendor_id"] == "V002"
assert result["vendor_name"] == "Metro Electrical Traders"

# Conflicting GSTIN
result = validate_vendor(
    vendor_name="Metro Electrical Traders",
    vendor_id="V002",
    tax_id="33ABCDE1234F1Z5",
    vendors_df=vendors_df
)

print(result)

assert result["status"] == "REVIEW"
assert result["vendor_id"] is None

print("\nAll vendor resolution tests passed.")