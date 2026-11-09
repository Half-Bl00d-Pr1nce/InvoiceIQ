
import pandas as pd


def _clean(value):
    """Convert an identifier into a clean string, or None."""
    if value is None or pd.isna(value):
        return None

    value = str(value).strip()

    if value.lower() in {"", "none", "null", "n/a"}:
        return None

    return value.upper()


def validate_vendor(
    vendor_name: str,
    vendors_df: pd.DataFrame,
    vendor_id: str = None,
    tax_id: str = None
) -> dict:
    """
    Validate a vendor using the vendor master.

    Vendor ID and GSTIN are authoritative identifiers.
    Vendor name is used as a fallback only when neither
    identifier is supplied.
    """

    vendor_id = _clean(vendor_id)
    tax_id = _clean(tax_id)
    vendor_name_clean = _clean(vendor_name)

    id_matches = pd.DataFrame()
    gstin_matches = pd.DataFrame()

    if vendor_id:
        id_matches = vendors_df[
            vendors_df["vendor_id"].apply(_clean) == vendor_id
        ]

    if tax_id:
        gstin_matches = vendors_df[
            vendors_df["gstin"].apply(_clean) == tax_id
        ]

    # Both identifiers are available.
    if vendor_id and tax_id:

        if len(id_matches) == 1 and len(gstin_matches) == 1:

            id_vendor = id_matches.iloc[0]
            gstin_vendor = gstin_matches.iloc[0]

            if id_vendor["vendor_id"] != gstin_vendor["vendor_id"]:
                return {
                    "check": "VENDOR_VALIDATION",
                    "status": "REVIEW",
                    "vendor_id": None,
                    "vendor_name": None,
                    "message": (
                        "Vendor ID and GSTIN identify different vendors."
                    )
                }

            vendor = id_vendor

        else:
            return {
                "check": "VENDOR_VALIDATION",
                "status": "REVIEW",
                "vendor_id": None,
                "vendor_name": None,
                "message": (
                    "Vendor ID or GSTIN could not be uniquely verified "
                    "against the vendor master."
                )
            }

    # Only Vendor ID is available.
    elif vendor_id:

        if len(id_matches) != 1:
            return {
                "check": "VENDOR_VALIDATION",
                "status": "FAIL",
                "vendor_id": None,
                "vendor_name": None,
                "message": "Vendor ID was not found uniquely in the vendor master."
            }

        vendor = id_matches.iloc[0]

    # Only GSTIN is available.
    elif tax_id:

        if len(gstin_matches) != 1:
            return {
                "check": "VENDOR_VALIDATION",
                "status": "FAIL",
                "vendor_id": None,
                "vendor_name": None,
                "message": "GSTIN was not found uniquely in the vendor master."
            }

        vendor = gstin_matches.iloc[0]

    # Fall back to exact vendor-name matching only when
    # neither authoritative identifier is available.
    elif vendor_name_clean:

        name_matches = vendors_df[
            vendors_df["vendor_name"].apply(_clean)
            == vendor_name_clean
        ]

        if len(name_matches) != 1:
            return {
                "check": "VENDOR_VALIDATION",
                "status": "FAIL" if name_matches.empty else "REVIEW",
                "vendor_id": None,
                "vendor_name": None,
                "message": "Vendor name could not be uniquely verified."
            }

        vendor = name_matches.iloc[0]

    else:
        return {
            "check": "VENDOR_VALIDATION",
            "status": "NOT_CHECKED",
            "vendor_id": None,
            "vendor_name": None,
            "message": "No vendor identifier or name was extracted."
        }

    # Check whether the matched vendor is active.
    if str(vendor["status"]).strip().upper() != "ACTIVE":
        return {
            "check": "VENDOR_VALIDATION",
            "status": "FAIL",
            "vendor_id": vendor["vendor_id"],
            "vendor_name": vendor["vendor_name"],
            "message": "Vendor exists but is not active."
        }

    official_name = vendor["vendor_name"]

    name_note = ""
    if vendor_name_clean and vendor_name_clean != _clean(official_name):
        name_note = (
            f" Extracted name '{vendor_name}' differed from the "
            f"vendor master; the master name was used."
        )

    return {
        "check": "VENDOR_VALIDATION",
        "status": "PASS",
        "vendor_id": vendor["vendor_id"],
        "vendor_name": official_name,
        "message": (
            f"Vendor '{official_name}' was verified against the "
            f"vendor master.{name_note}"
        )
    }
