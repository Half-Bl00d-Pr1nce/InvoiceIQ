
from pathlib import Path
import yaml


def load_rules():
    """Load business rules from rules.yaml."""

    config_path = Path("config/rules.yaml")

    with open(config_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def make_decision(validation_results, rules=None):
    """
    Determine the final invoice decision using deterministic rules.

    Expected validation_results structure:

    {
        "duplicate": {"status": "PASS"},
        "vendor": {"status": "PASS"},
        "po": {"status": "PASS"},
        "financial": {"status": "PASS"},
        "item_reconciliation": {"status": "PASS"},
        "extraction": {"status": "PASS"}
    }
    """

    if rules is None:
        rules = load_rules()

    decision_rules = rules["decision"]

    rejected_reasons = []
    review_reasons = []

    # 1. Duplicate detection
    duplicate = validation_results.get("duplicate", {})
    duplicate_status = duplicate.get("status", "NOT_CHECKED")

    if duplicate_status == "FAIL":
        rejected_reasons.append(
            duplicate.get("message", "Duplicate invoice detected.")
        )
    elif duplicate_status != "PASS":
        review_reasons.append(
            duplicate.get("message", "Duplicate check was not completed.")
        )

    # 2. Vendor validation
    vendor = validation_results.get("vendor", {})
    vendor_status = vendor.get("status", "NOT_CHECKED")

    if vendor_status == "FAIL":
        rejected_reasons.append(
            vendor.get("message", "Vendor validation failed.")
        )
    elif vendor_status != "PASS":
        review_reasons.append(
            vendor.get("message", "Vendor validation requires review.")
        )

    # 3. Purchase order validation
    po = validation_results.get("po", {})
    po_status = po.get("status", "NOT_CHECKED")

    if po_status == "FAIL":
        rejected_reasons.append(
            po.get("message", "Purchase order validation failed.")
        )
    elif po_status != "PASS":
        review_reasons.append(
            po.get("message", "Purchase order validation is incomplete.")
        )

    # 4. Financial validation
    financial = validation_results.get("financial", {})
    financial_status = financial.get("status", "NOT_CHECKED")

    if financial_status == "FAIL":
        review_reasons.append(
            financial.get("message", "Financial validation failed.")
        )
    elif financial_status != "PASS":
        review_reasons.append(
            financial.get("message", "Financial validation is incomplete.")
        )

    # 5. Item reconciliation, including cumulative checks
    reconciliation = validation_results.get(
        "item_reconciliation", {}
    )
    reconciliation_status = reconciliation.get(
        "status", "NOT_CHECKED"
    )

    if reconciliation_status == "FAIL":
        review_reasons.append(
            reconciliation.get(
                "message",
                "PO item reconciliation failed."
            )
        )
    elif reconciliation_status != "PASS":
        review_reasons.append(
            reconciliation.get(
                "message",
                "PO item reconciliation requires review."
            )
        )

    # 6. Extraction confidence / critical fields
    extraction = validation_results.get("extraction", {})
    extraction_status = extraction.get("status", "NOT_CHECKED")

    if extraction_status != "PASS":
        review_reasons.append(
            extraction.get(
                "message",
                "Extraction is incomplete or uncertain."
            )
        )

    # 7. Final decision
    if rejected_reasons:
        status = decision_rules["duplicate"] if (
            duplicate_status == "FAIL"
        ) else decision_rules["vendor_mismatch"] if (
            vendor_status == "FAIL"
        ) else "REJECTED"

    elif review_reasons:
        status = "PENDING_REVIEW"

    else:
        status = "APPROVED"

    return {
        "status": status,
        "rejection_reasons": rejected_reasons,
        "review_reasons": review_reasons,
        "validation_results": validation_results
    }
