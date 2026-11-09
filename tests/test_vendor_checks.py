import pandas as pd

from src.validation.vendor_checks import validate_vendor


def create_vendor_master():
    return pd.DataFrame([
        {
            "vendor_id": "V001",
            "vendor_name": "Chennai Industrial Supplies",
            "gstin": "33ABCDE1234F1Z5",
            "status": "ACTIVE",
            "bank_ref": "BANKREF-001"
        },
        {
            "vendor_id": "V002",
            "vendor_name": "Metro Electrical Traders",
            "gstin": "33BCDEF2345G1Z6",
            "status": "ACTIVE",
            "bank_ref": "BANKREF-002"
        }
    ])


def test_active_vendor():
    vendors = create_vendor_master()

    result = validate_vendor("Chennai Industrial Supplies", vendors)

    assert result["status"] == "PASS"
    assert result["vendor_id"] == "V001"


def test_unknown_vendor():
    vendors = create_vendor_master()

    result = validate_vendor("BioHue Chemicals", vendors)

    assert result["status"] == "FAIL"
    assert result["vendor_id"] is None


def test_case_insensitive_matching():
    vendors = create_vendor_master()

    result = validate_vendor("metro electrical traders", vendors)

    assert result["status"] == "PASS"
    assert result["vendor_id"] == "V002"


def test_missing_vendor():
    vendors = create_vendor_master()

    result = validate_vendor("", vendors)

    assert result["status"] == "NOT_CHECKED"


def test_inactive_vendor():
    vendors = create_vendor_master()
    vendors.loc[vendors["vendor_id"] == "V001", "status"] = "INACTIVE"

    result = validate_vendor("Chennai Industrial Supplies", vendors)

    assert result["status"] == "FAIL"
    assert result["vendor_id"] == "V001"


def test_duplicate_vendor_records():
    vendors = create_vendor_master()

    duplicate = vendors[vendors["vendor_id"] == "V001"]
    vendors = pd.concat([vendors, duplicate], ignore_index=True)

    result = validate_vendor("Chennai Industrial Supplies", vendors)

    assert result["status"] == "REVIEW"
    assert result["vendor_id"] is None