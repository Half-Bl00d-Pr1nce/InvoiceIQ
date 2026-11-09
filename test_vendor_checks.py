import pandas as pd
from copy import deepcopy
from src.validation.vendor_checks import validate_vendor


vendors_df = pd.read_csv("data/vendors.csv")


# Test 1: Approved vendor
result = validate_vendor("Chennai Industrial Supplies", vendors_df)
print("\nACTIVE VENDOR:", result)


# Test 2: Unknown vendor
result = validate_vendor("BioHue Chemicals", vendors_df)
print("\nUNKNOWN VENDOR:", result)


# Test 3: Case-insensitive matching
result = validate_vendor("metro electrical traders", vendors_df)
print("\nCASE-INSENSITIVE MATCH:", result)


# Test 4: Missing vendor
result = validate_vendor("", vendors_df)
print("\nMISSING VENDOR:", result)

# Test 5: Inactive vendor
inactive_vendors = deepcopy(vendors_df)
inactive_vendors.loc[
    inactive_vendors["vendor_id"] == "V001", "status"
] = "INACTIVE"

result = validate_vendor("Chennai Industrial Supplies", inactive_vendors)
print("\nINACTIVE VENDOR:", result)


# Test 6: Duplicate vendor records
duplicate_vendors = pd.concat(
    [vendors_df, vendors_df[vendors_df["vendor_id"] == "V001"]],
    ignore_index=True
)

result = validate_vendor("Chennai Industrial Supplies", duplicate_vendors)
print("\nDUPLICATE VENDOR RECORD:", result)